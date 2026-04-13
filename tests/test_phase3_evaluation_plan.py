from benchmarks import evaluate_phase3_strategies as mod


def test_select_best_promoted_nc_returns_best_ok_result():
    results = [
        {"status": "ok", "nc": [1, 1, 2, 4], "J_validated": 0.2},
        {"status": "error", "nc": [1, 1, 3, 3], "J_validated": None},
        {"status": "ok", "nc": [2, 1, 3, 2], "J_validated": 0.5},
    ]

    winner = mod.select_best_promoted_nc(results)

    assert winner is not None
    assert winner["nc"] == [2, 1, 3, 2]
    assert winner["J_validated"] == 0.5


def test_build_strategy_summary_reports_promotion_and_robustness():
    promoted = [
        {"status": "ok", "nc": [1, 1, 2, 4], "strategy": "a", "J_validated": 0.2},
        {"status": "ok", "nc": [2, 1, 3, 2], "strategy": "a", "J_validated": 0.5},
    ]
    finalist = [
        {"status": "ok", "nc": [2, 1, 3, 2], "strategy": "a", "run": 1, "J_validated": 0.45},
        {"status": "ok", "nc": [2, 1, 3, 2], "strategy": "a", "run": 2, "J_validated": 0.50},
        {"status": "ok", "nc": [2, 1, 3, 2], "strategy": "a", "run": 3, "J_validated": 0.48},
    ]

    summary = mod.build_strategy_summary(promoted, finalist)

    assert summary["best_promoted_nc"] == [2, 1, 3, 2]
    assert summary["best_promoted_j"] == 0.5
    assert summary["promotion_stage"]["n_successful"] == 2
    assert summary["finalist_robustness"]["n_successful"] == 3
    assert summary["finalist_robustness"]["best_j"] == 0.5


def test_compute_statistics_uses_best_promoted_and_finalist_means():
    promotion_results = {
        "a": [
            {"status": "ok", "strategy": "a", "J_validated": 0.3},
            {"status": "ok", "strategy": "a", "J_validated": 0.5},
        ],
        "b": [
            {"status": "ok", "strategy": "b", "J_validated": 0.4},
        ],
        "c": [
            {"status": "ok", "strategy": "c", "J_validated": 0.35},
        ],
    }
    finalist_results = {
        "a": [
            {"status": "ok", "strategy": "a", "J_validated": 0.45},
            {"status": "ok", "strategy": "a", "J_validated": 0.5},
        ],
        "b": [
            {"status": "ok", "strategy": "b", "J_validated": 0.39},
        ],
        "c": [
            {"status": "ok", "strategy": "c", "J_validated": 0.36},
        ],
    }

    stats = mod.compute_statistics(promotion_results, finalist_results)

    assert stats["a"]["best_promoted_j"] == 0.5
    assert stats["a"]["finalist_mean_j"] == 0.475
    assert stats["b"]["promotion_n"] == 1
