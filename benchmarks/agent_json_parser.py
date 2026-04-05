"""
Enhanced JSON parsing and repair for agent responses.

Handles LLM output with multiple fallback strategies:
1. Direct parse
2. Auto-repair (fix common syntax errors)
3. Regex extraction
4. Graceful degradation to defaults

This prevents expensive repair cycles while maintaining robustness.
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


def auto_repair_json(response: str) -> str:
    """
    Auto-fix common JSON syntax errors without re-querying LLM.

    Fixes:
    - Missing closing braces
    - Trailing commas
    - Unescaped quotes in strings (basic)
    - Trailing newlines/whitespace
    """
    # Remove leading/trailing whitespace and markdown backticks
    repaired = response.strip()
    if repaired.startswith("```json"):
        repaired = repaired[7:]
    if repaired.startswith("```"):
        repaired = repaired[3:]
    if repaired.endswith("```"):
        repaired = repaired[:-3]
    repaired = repaired.strip()

    # Fix missing closing braces
    open_braces = repaired.count("{")
    close_braces = repaired.count("}")
    if open_braces > close_braces:
        repaired += "}" * (open_braces - close_braces)

    # Fix trailing commas before closing braces/brackets
    repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)

    # Fix trailing commas in arrays
    repaired = re.sub(r',(\s*\])', r'\1', repaired)

    return repaired


def extract_json_via_regex(response: str, required_keys: Sequence[str]) -> Optional[Dict[str, Any]]:
    """
    Extract required fields from response using regex as last resort.

    Used when json.loads() completely fails. Builds a minimal dict
    from captured key-value pairs.
    """
    extracted = {}

    for key in required_keys:
        # Try to find this key in the response
        # Patterns: "key": value or 'key': value
        patterns = [
            rf'"{key}"\s*:\s*"([^"]*)"',          # string value
            rf'"{key}"\s*:\s*(\d+(?:\.\d+)?)',    # number
            rf'"{key}"\s*:\s*(\[[^\]]*\])',       # array
            rf'"{key}"\s*:\s*(\{{\s*[^}}]*}})',   # object
            rf'"{key}"\s*:\s*(true|false)',       # boolean
            rf'"{key}"\s*:\s*(null)',             # null
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                try:
                    value = match.group(1)
                    # Try to parse as JSON if it looks like structured data
                    if value.startswith('[') or value.startswith('{'):
                        extracted[key] = json.loads(value)
                    elif value.lower() in ('true', 'false'):
                        extracted[key] = value.lower() == 'true'
                    elif value.lower() == 'null':
                        extracted[key] = None
                    else:
                        # Try numeric
                        try:
                            extracted[key] = float(value) if '.' in value else int(value)
                        except (ValueError, TypeError):
                            extracted[key] = value
                    break
                except (json.JSONDecodeError, IndexError, AttributeError):
                    continue

    # Only return if we got most of the required keys
    if len(extracted) >= len(required_keys) * 0.7:
        return extracted

    return None


def parse_json_with_fallbacks(
    response: str,
    required_keys: Sequence[str],
    max_attempts: int = 3,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Parse JSON from LLM response with multiple fallback strategies.

    Returns:
        (parsed_dict, status) where status is one of:
        - "success" — direct parse
        - "success_auto_repair" — fixed syntax errors
        - "success_regex" — extracted via regex
        - "partial" — got some required keys
        - "fail" — could not parse
    """

    # Strategy 1: Direct parse
    try:
        data = json.loads(response)
        if isinstance(data, dict):
            return data, "success"
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Auto-repair common syntax errors
    for attempt in range(max_attempts):
        try:
            repaired = auto_repair_json(response)
            data = json.loads(repaired)
            if isinstance(data, dict):
                return data, "success_auto_repair"
        except (json.JSONDecodeError, ValueError):
            continue

    # Strategy 3: Extract via regex
    extracted = extract_json_via_regex(response, required_keys)
    if extracted:
        return extracted, "success_regex"

    # Strategy 4: Return None with failure reason
    return None, "fail"


def validate_required_keys(
    data: Optional[Dict[str, Any]],
    required_keys: Sequence[str],
) -> Tuple[bool, Optional[Sequence[str]]]:
    """
    Check if dict has all required keys.

    Returns:
        (is_valid, missing_keys)
    """
    if not isinstance(data, dict):
        return False, list(required_keys)

    missing = [k for k in required_keys if k not in data]
    return len(missing) == 0, missing if missing else None


def apply_defaults_for_missing_keys(
    data: Optional[Dict[str, Any]],
    required_keys: Sequence[str],
    defaults: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fill in missing required keys with sensible defaults.

    Args:
        data: Parsed JSON dict (may be None)
        required_keys: List of keys that must be present
        defaults: Custom defaults per key, defaults to generic placeholders
    """
    if not isinstance(data, dict):
        data = {}

    if defaults is None:
        defaults = {}

    for key in required_keys:
        if key not in data:
            if key in defaults:
                data[key] = defaults[key]
            elif 'reason' in key or 'physics' in key or 'justification' in key:
                data[key] = "<response parsing failed>"
            elif 'index' in key or 'count' in key:
                data[key] = 0
            elif any(x in key for x in ('list', 'array', 'items', 'refs', 'audit', 'arguments', 'checks', 'updates', 'flags')):
                data[key] = []
            elif any(x in key for x in ('run', 'config', 'counterproposal')):
                data[key] = {}
            elif 'decision' in key:
                data[key] = "reject"
            elif 'confidence' in key or 'probability' in key:
                data[key] = 0.0
            else:
                data[key] = None

    return data


# === Few-shot examples for prompts ===

SCIENTIST_B_REVIEW_EXAMPLES = """
### Example 1: APPROVE with concerns
{
  "decision": "approve",
  "reason": "Explores F1=2.0 (vs reference 2.5). R-1 at [2,2,2,2] F1=2.5 achieved J=45.2, purity=0.61. This variation tests hypothesis H3.",
  "evidence_refs": ["smb_qwen_run_0047", "smb_qwen_run_0031"],
  "comparison_assessment": [
    "vs R-1 [2,2,2,2] F1=2.5: ΔF1=-0.5 (tighter), expect ΔJ≈-5%, ΔpurityΔ+2%",
    "vs R-2 [1,3,2,2] F1=2.0: Same F1, different nc topology; R-2 was infeasible"
  ],
  "last_two_run_audit": [
    "R-1: smb_qwen_run_0047 [2,2,2,2] F1=2.5 feasible=yes prod=45.2 purity=0.610 viol=0.0%",
    "R-2: smb_qwen_run_0031 [1,3,2,2] F1=2.0 feasible=no prod=undef purity=undef viol=45.3% (zone_II_infeas)"
  ],
  "flowrate_audit": ["ΔFfeed=-0.15, ΔF1=-0.50, ΔFdes=-0.30, ΔFex=+0.10, ΔFraf=-0.05, Δtstep=0.0"],
  "delta_audit": [
    "vs R-1: Δprod=-4.2%, Δpurity=+1.8%, ΔrGA=+0.5%, ΔrMA=-0.3%, Δviol=0.0%",
    "vs R-2: Δprod=undefined (R-2 infeasible), Δpurity=N/A, ΔrGA=N/A, ΔrMA=N/A, Δviol=-45.3% (improvement)"
  ],
  "column_topology_audit": [
    "vs R-1: nc=[2,2,2,2]->[2,2,2,2], ΔZ1=-0.8cm (tighter buffer), ΔZ2=0.0, ΔZ3=+0.3cm (wider), ΔZ4=0.0",
    "vs R-2: nc=[1,3,2,2] (different topology entirely), R-2 was infeasible"
  ],
  "physics_audit": "Zone I feed: F1×c1_in = balance OK. Zone II desorbent: Fdes×c_des balanced within ±1.2%. Selectivity: α_GA/MA ≈ 1.8 (nominal). No retrograde or channeling predicted.",
  "counterproposal_run": {
    "nc": [2,2,2,2],
    "flow_adjustments": {"Ffeed": 0.0, "F1": -0.50, "Fdes": -0.30, "Fex": 0.0, "Fraf": 0.0, "tstep": 0.0},
    "expected_metric_effect": {"delta_productivity": -3.5, "delta_purity": +0.025, "delta_recovery_ga": +0.03, "delta_recovery_ma": -0.02, "delta_violation": 0.0},
    "physics_justification": "Tighter F1 reduces axial dispersion in extract zone while maintaining mass balance. Literature (Smith et al. 2021) shows 2-5% J reduction acceptable for >2% purity gain."
  },
  "nc_strategy_assessment": ["[2,2,2,2] well-explored (12 runs), good baseline", "[1,3,2,2] topology infeasible at this feed; skip", "Propose next: [3,2,2,1] to shift desorbent/extract balance"],
  "compute_assessment": "Estimated 90-120s solver time (similar to R-1). Within budget.",
  "counterarguments": [
    "Lower F1 reduces throughput, may hurt recovery targets",
    "R-2 infeasibility at this F1 suggests mass balance risk"
  ],
  "required_checks": [
    "Verify mass balance post-solve: ΔF1 consistency in solver output",
    "Check extract outlet concentration profiles for breakthrough"
  ],
  "priority_updates": ["H3 (F1 sensitivity): +1 evidence point, approve", "H7 (topology screening): R-2 failure confirms [1,3,2,2] skip"],
  "risk_flags": ["mass_balance_sensitivity", "throughput_tradeoff"]
}

### Example 2: REJECT with reasoning
{
  "decision": "reject",
  "reason": "Duplicate of R-1. Same nc=[2,2,2,2], F1=2.5 already evaluated with J=45.2. No new evidence.",
  "evidence_refs": ["smb_qwen_run_0047"],
  "comparison_assessment": ["vs R-1: Identical config, no variation"],
  "last_two_run_audit": [
    "R-1: smb_qwen_run_0047 [2,2,2,2] F1=2.5 feasible=yes prod=45.2 purity=0.610 viol=0.0%",
    "R-2: smb_qwen_run_0031 [1,3,2,2] F1=2.0 feasible=no prod=undef purity=undef viol=45.3%"
  ],
  "flowrate_audit": ["ΔFfeed=0.0, ΔF1=0.0, ΔFdes=0.0, ΔFex=0.0, ΔFraf=0.0, Δtstep=0.0 (no change)"],
  "delta_audit": ["vs R-1: No change (identical run)"],
  "column_topology_audit": ["vs R-1: no change (identical nc=[2,2,2,2])"],
  "physics_audit": "Identical to R-1; no new insights.",
  "counterproposal_run": {
    "nc": [2,2,1,3],
    "flow_adjustments": {"Ffeed": 0.0, "F1": -0.30, "Fdes": +0.20, "Fex": -0.10, "Fraf": 0.0, "tstep": 0.0},
    "expected_metric_effect": {"delta_productivity": -2.0, "delta_purity": +0.04, "delta_recovery_ga": 0.0, "delta_recovery_ma": +0.05, "delta_violation": 0.0},
    "physics_justification": "Different topology [2,2,1,3] with reduced F1 and higher Fdes increases selectivity. Hypothesis H5 predicts +3-5% purity at <2% J cost."
  },
  "nc_strategy_assessment": ["[2,2,2,2] saturated (12 runs already)", "[2,2,1,3] novel topology, untested; good next step"],
  "compute_assessment": "Estimated 90-150s; within budget.",
  "counterarguments": ["Proposing duplicate wastes computational budget"],
  "required_checks": ["Verify counter-proposal topology is feasible before commit"],
  "priority_updates": ["H1 (search efficiency): penalize duplicate proposals"],
  "risk_flags": ["duplicate_detection_failed"]
}
""".strip()


SCIENTIST_A_PROPOSAL_EXAMPLES = """
### Example 1: Exploratory proposal
{
  "nc": [1,2,3,2],
  "seed_name": "ref_high_affinity",
  "reasoning": "Exploring lower Z1 (1 vs typical 2-3) to test hypothesis H2: reduced buffer zone may improve selectivity. Prior run [2,2,3,2] achieved J=52.1, purity=0.65. This variant reduces zone-I overhead.",
  "hypothesis_tested": "H2",
  "acquisition_strategy": "EXPLORE",
  "acquisition_rationale": "New topology region; literature (Lee et al. 2020) suggests Z1=1-2 may be optimal for tight separations.",
  "confidence": 0.68,
  "expected_metrics": {
    "productivity": 50.5,
    "purity": 0.68,
    "recovery_ga": 0.76,
    "recovery_ma": 0.79,
    "violation": 0.0
  },
  "required_solver_checks": ["zone_I_residence_time", "breakthrough_check_extract"],
  "risk_assessment": "Medium: lower Z1 may trigger channeling if residence time <0.5s"
}

### Example 2: Exploitation of known good region
{
  "nc": [2,2,2,2],
  "seed_name": "ref_standard",
  "reasoning": "Refining successful [2,2,2,2] baseline. Prior best J=45.2 (run_0047). This adjusts F1=2.2 (vs 2.5) to explore purity-productivity tradeoff within proven topology.",
  "hypothesis_tested": "H3",
  "acquisition_strategy": "EXPLOIT",
  "acquisition_rationale": "Verified topology with room for parameter optimization. Incremental F1 change (±0.3) has <5% risk.",
  "confidence": 0.85,
  "expected_metrics": {
    "productivity": 44.0,
    "purity": 0.63,
    "recovery_ga": 0.75,
    "recovery_ma": 0.78,
    "violation": 0.0
  },
  "required_solver_checks": ["mass_balance_consistency"],
  "risk_assessment": "Low: well-characterized topology"
}
""".strip()


def add_few_shot_examples_to_prompt(
    prompt: str,
    role: str = "scientist_b_review",
) -> str:
    """
    Insert few-shot JSON examples into a prompt to teach format.

    Args:
        prompt: Original prompt text
        role: "scientist_b_review" or "scientist_a_proposal"

    Returns:
        Prompt with examples inserted before the JSON template
    """
    if role == "scientist_b_review":
        examples = SCIENTIST_B_REVIEW_EXAMPLES
        insertion_text = "## Example valid responses:\n\n" + examples + "\n\n## Your response:\n"
    elif role == "scientist_a_proposal":
        examples = SCIENTIST_A_PROPOSAL_EXAMPLES
        insertion_text = "## Example valid proposals:\n\n" + examples + "\n\n## Your proposal:\n"
    else:
        return prompt

    # Find where the JSON template starts and insert examples before it
    json_template_markers = ["Respond with this JSON", "Return ONLY", "Output format:"]
    for marker in json_template_markers:
        if marker in prompt:
            idx = prompt.find(marker)
            return prompt[:idx] + insertion_text + prompt[idx:]

    return prompt


if __name__ == "__main__":
    # Test the parser
    test_cases = [
        ('{"key": "value"}', True),
        ('{"key": "value"', False),  # missing }
        ('{"key": "value",}', False),  # trailing comma
        ('{"key": "value"}}', False),  # extra }
    ]

    for test_input, should_parse in test_cases:
        data, status = parse_json_with_fallbacks(test_input, ["key"])
        print(f"Input: {test_input}")
        print(f"  Status: {status}, Parsed: {data is not None}")
        print()
