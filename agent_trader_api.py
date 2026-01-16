from agents import (
    Portfolio,
    Trade,
    RiskManagerAgent,
    RiskConfig,
)
from alpaca_stub import AlpacaStub
from agents import trend_agent, decision_agent

def main():
    portfolio = Portfolio(
        cash=100_000,
        holdings={},
        total_value=100_000,
    )

    print("Fetching real market data (cached)...")

    # agents analyze
    signals = trend_agent(["PLTR", "NFLX", "PLTK"])

    # decision agent proposes trades
    proposed_trades = decision_agent(signals, portfolio)

    # risk manager approves
    risk_agent = RiskManagerAgent(RiskConfig())
    decisions = risk_agent.evaluate_trades(
        portfolio=portfolio,
        trades=proposed_trades,
        trade_history=[],
    )

    # execute paper trades
    alpaca = AlpacaStub()
    for d in decisions:
        if d.approved:
            alpaca.submit_trade(
                d.symbol, d.side, d.final_amount
            )

    print("Run completed.")


if __name__ == "__main__":
    main()
