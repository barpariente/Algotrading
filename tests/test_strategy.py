from models import Signal
from strategy import decide_trades, news_action, trend_action


def test_trend_buys_on_rising_closes():
    assert trend_action([100, 101, 103]) == "BUY"


def test_trend_sells_on_falling_closes():
    assert trend_action([100, 99, 97]) == "SELL"


def test_trend_holds_on_flat_or_short_window():
    assert trend_action([100, 105, 100]) == "HOLD"
    assert trend_action([100]) == "HOLD"


def test_news_counts_positive_and_negative_headlines():
    assert news_action(["Revenue beat estimates", "Growth accelerates"]) == "BUY"
    assert news_action(["Lawsuit filed", "Shares down 5%"]) == "SELL"
    assert news_action(["Earnings call today"]) == "HOLD"


def test_trend_signal_alone_is_enough_to_trade():
    trades = decide_trades([Signal("PLTR", "BUY", 0.6)])
    assert [(t.symbol, t.side, t.amount) for t in trades] == [("PLTR", "BUY", 5_000)]


def test_news_signal_alone_is_not_enough_to_trade():
    assert decide_trades([Signal("PLTR", "BUY", 0.4)]) == []


def test_conflicting_signals_cancel_out():
    assert decide_trades([Signal("NFLX", "BUY", 0.6), Signal("NFLX", "SELL", 0.4)]) == []
