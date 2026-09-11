import pytest

from sunimuhendis.environments.heat_exchanger.score import HeatExchangerScoreV3


def _task(**overrides):
    task = {
        "w_heat": 0.5,
        "w_drop_tube": 0.175,
        "w_drop_shell": 0.175,
        "w_eff": 0.05,
        "w_cost": 0.1,
        "target_heat_duty": 350000.0,
        "max_dp_tube": 2500.0,
        "max_dp_shell": 2500.0,
        "cost_good": 5000.0,
        "cost_bad": 15000.0,
        "warning_penalty_per_warning": 0.1,
        "unmet_penalty_per_requirement": 0.1,
    }
    task.update(overrides)
    return task


def _metrics(**overrides):
    metrics = {
        "heat_duty_W": 350000.0,
        "dp_tube_Pa": 2500.0,
        "dp_shell_Pa": 2500.0,
        "effectiveness": 1.0,
        "cost_annualised_USD_per_yr": 5000.0,
        "num_warnings": 0.0,
    }
    metrics.update(overrides)
    return metrics


def test_v3_perfect_design_scores_one():
    result = HeatExchangerScoreV3().calculate_score(_task(), _metrics())

    assert result.normalized_total == pytest.approx(1.0)
    assert result.components["num_unmet_requirements"] == 0.0
    assert result.components["penalty_factor"] == pytest.approx(1.0)


def test_v3_unmet_requirement_adds_ten_percent_penalty():
    task = _task(
        w_heat=1.0,
        w_drop_tube=0.0,
        w_drop_shell=0.0,
        w_eff=0.0,
        w_cost=0.0,
    )
    result = HeatExchangerScoreV3().calculate_score(
        task, _metrics(heat_duty_W=315000.0)
    )

    assert result.components["heat_duty_reward"] == pytest.approx(0.9)
    assert result.components["num_unmet_requirements"] == 1.0
    assert result.components["requirement_penalty_total"] == pytest.approx(0.1)
    assert result.normalized_total == pytest.approx(0.9 * 0.9)


def test_v3_warnings_and_unmet_requirements_share_penalty_scale():
    result = HeatExchangerScoreV3().calculate_score(
        _task(),
        _metrics(
            heat_duty_W=300000.0,
            dp_tube_Pa=3000.0,
            dp_shell_Pa=3000.0,
            num_warnings=2.0,
        ),
    )

    assert result.components["num_unmet_requirements"] == 3.0
    assert result.components["warning_penalty_total"] == pytest.approx(0.2)
    assert result.components["requirement_penalty_total"] == pytest.approx(0.3)
    assert result.components["penalty_factor"] == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("cost", "expected"),
    [(4000.0, 1.0), (5000.0, 1.0), (10000.0, 0.5), (15000.0, 0.0), (20000.0, 0.0)],
)
def test_v3_cost_reward_uses_calibrated_range(cost, expected):
    result = HeatExchangerScoreV3().calculate_score(
        _task(), _metrics(cost_annualised_USD_per_yr=cost)
    )

    assert result.components["cost_reward_raw"] == pytest.approx(expected)
    assert result.components["cost_reward"] == pytest.approx(expected)


def test_v3_cost_reward_is_gated_by_performance():
    result = HeatExchangerScoreV3().calculate_score(
        _task(), _metrics(heat_duty_W=175000.0, cost_annualised_USD_per_yr=4000.0)
    )

    assert result.components["cost_reward_raw"] == pytest.approx(1.0)
    assert result.components["cost_performance_gate"] == pytest.approx(0.5)
    assert result.components["cost_reward"] == pytest.approx(0.5)


def test_v3_invalid_design_scores_zero():
    result = HeatExchangerScoreV3().calculate_score(
        _task(), {}, is_valid=False, error_message="invalid"
    )

    assert result.normalized_total == 0.0
    assert result.is_valid is False
    assert result.error_message == "invalid"
