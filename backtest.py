from alpaca_stub import AlpacaStub
from crew import create_crew
from state import STATE

def run_backtest():
    alpaca = AlpacaStub()

    for _ in range(24 * 7):
        STATE["portfolio"] = alpaca.get_portfolio()
        STATE["signals"] = []
        STATE["trades"] = []
        STATE["decisions"] = []

        create_crew().kickoff()

        for d in STATE["decisions"]:
            if d.approved:
                alpaca.submit_trade(d)

    print("Final portfolio:", alpaca.get_portfolio())

if __name__ == "__main__":
    run_backtest()
