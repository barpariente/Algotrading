from agents import RiskManagerAgent, RiskConfig
from models import Portfolio, Trade


def test_adjusts_sell_to_owned_amount():
    portfolio = Portfolio(cash=30_000, holdings={"PLTK": 4_000}, total_value=100_000)
    trade = Trade(symbol="PLTK", side="SELL", amount=10_000)

    agent = RiskManagerAgent(RiskConfig())
    decisions = agent.evaluate_trades(portfolio=portfolio, trades=[trade], trade_history=[])

    assert decisions[0].approved is True
    assert decisions[0].final_amount == 4_000
