import time
from alpaca_stub import AlpacaStub
from crew import create_crew
from state import STATE

def main():
    alpaca = AlpacaStub()
    print("Starting trading bot")

    while True:
        STATE["portfolio"] = alpaca.get_portfolio()
        STATE["signals"] = []
        STATE["trades"] = []
        STATE["decisions"] = []

        crew = create_crew()
        crew.kickoff()

        for d in STATE["decisions"]:
            if d.approved:
                alpaca.submit_trade(d)

        print("Portfolio:", alpaca.get_portfolio())
        time.sleep(10)

if __name__ == "__main__":
    main()
