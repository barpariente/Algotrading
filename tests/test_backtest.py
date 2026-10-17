import pytest

from backtest import STARTING_CASH, load_prices, max_drawdown, run_backtest


def test_max_drawdown_measures_worst_peak_to_trough():
    assert max_drawdown([100, 120, 90, 130]) == pytest.approx(-0.25)


def test_max_drawdown_is_zero_when_only_rising():
    assert max_drawdown([100, 110, 120]) == 0.0


def test_flat_prices_never_trade():
    result = run_backtest({"AAA": [10.0] * 30})
    assert result.trades_executed == 0
    assert result.final_value == STARTING_CASH


def test_rising_market_buys_until_exposure_cap():
    prices = {"AAA": [10.0 + i for i in range(60)]}
    result = run_backtest(prices)
    assert result.trades_executed > 0
    assert result.trades_rejected > 0
    assert result.total_return > 0


def test_falling_market_never_sells_what_it_does_not_own():
    result = run_backtest({"AAA": [100.0 - i for i in range(30)]})
    assert result.trades_executed == 0
    assert result.final_value == STARTING_CASH


def test_2025_backtest_is_reproducible():
    _, prices = load_prices("data/prices_2025.csv")
    result = run_backtest(prices)
    assert result.total_return == pytest.approx(0.163, abs=0.001)
    assert result.benchmark_return == pytest.approx(0.351, abs=0.001)
