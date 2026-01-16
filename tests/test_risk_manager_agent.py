import pytest
from datetime import datetime, timedelta

from agents import RiskManagerAgent , RiskConfig
from models import Portfolio, Trade

def test_approves_safe_buy():
    portfolio = Portfolio(
        cash=50_000,
        holdings={"PLTR": 20_000},
        total_value=100_000
    )

    trade = Trade(symbol="NFLX", side="BUY", amount=5_000)

    agent = RiskManagerAgent(RiskConfig())

    decisions = agent.evaluate_trades(
        portfolio=portfolio,
        trades=[trade],
        trade_history=[]
    )

    decision = decisions[0]
    assert decision.approved is True
    assert decision.final_amount == 5_000

def test_adjusts_trade_when_exceeding_max_exposure():
    portfolio = Portfolio(
        cash=50_000,
        holdings={"PLTR": 28_000},
        total_value=100_000
    )

    trade = Trade(symbol="PLTR", side="BUY", amount=10_000)

    agent = RiskManagerAgent(
        RiskConfig(max_exposure_pct=0.30)
    )

    decisions = agent.evaluate_trades(
        portfolio=portfolio,
        trades=[trade],
        trade_history=[]
    )

    decision = decisions[0]
    assert decision.approved is True
    assert decision.final_amount == 2_000

def test_rejects_trade_if_cash_below_reserve():
    portfolio = Portfolio(
        cash=12_000,
        holdings={"NFLX": 40_000},
        total_value=100_000
    )

    trade = Trade(symbol="PLTR", side="BUY", amount=5_000)

    agent = RiskManagerAgent(
        RiskConfig(min_cash_pct=0.10)
    )

    decisions = agent.evaluate_trades(
        portfolio=portfolio,
        trades=[trade],
        trade_history=[]
    )

    decision = decisions[0]
    assert decision.approved is False
    assert decision.final_amount == 0

def test_adjusts_sell_to_owned_amount():
    portfolio = Portfolio(
        cash=30_000,
        holdings={"PLTK": 4_000},
        total_value=100_000
    )

    trade = Trade(symbol="PLTK", side="SELL", amount=10_000)

    agent = RiskManagerAgent(RiskConfig())

    decisions = agent.evaluate_trades(
        portfolio=portfolio,
        trades=[trade],
        trade_history=[]
    )

    decision = decisions[0]
    assert decision.approved is True
    assert decision.final_amount == 4_000

def test_rejects_trades_when_trade_limit_exceeded():
    portfolio = Portfolio(
        cash=50_000,
        holdings={},
        total_value=100_000
    )

    trade = Trade(symbol="NFLX", side="BUY", amount=2_000)

    trade_history = [
        datetime.utcnow() - timedelta(minutes=5)
        for _ in range(5)
    ]

    agent = RiskManagerAgent(
        RiskConfig(max_trades_per_hour=5)
    )

    decisions = agent.evaluate_trades(
        portfolio=portfolio,
        trades=[trade],
        trade_history=trade_history
    )

    decision = decisions[0]
    assert decision.approved is False

