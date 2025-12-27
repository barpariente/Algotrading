from services.alpaca_stub import AlpacaStub
from crew_agents.crew import create_trading_crew
from agent_state import STATE


def main():
    alpaca = AlpacaStub(initial_cash=100_000)
    STATE["portfolio"] = alpaca.get_portfolio()

    crew = create_trading_crew()
    crew.kickoff()

    for decision in STATE.get("decisions", []):
        if decision.approved:
            alpaca.submit_trade(
                trade=decision 
            )

    STATE["portfolio"] = alpaca.get_portfolio()
    print("Final portfolio:", STATE["portfolio"])


if __name__ == "__main__":
    main()
