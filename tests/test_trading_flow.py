from unittest.mock import MagicMock
from models import Trade, Portfolio, RiskDecision
from alpaca_stub import AlpacaStub
from state import STATE
from crew import create_crew


def test_trade_is_submitted_when_approved():
    alpaca = AlpacaStub()
    alpaca.submit_trade = MagicMock()

    STATE["portfolio"] = Portfolio(
        cash=100_000,
        holdings={},
        total_value=100_000,
    )

    STATE["signals"] = []
    STATE["trades"] = []
    STATE["decisions"] = [
        RiskDecision(
            symbol="PLTR",
            side="BUY",
            approved=True,
            final_amount=5000,
            reason="Approved",
        )
    ]

    for decision in STATE["decisions"]:
        if decision.approved:
            alpaca.submit_trade(decision)
    alpaca.submit_trade.assert_called_once()
