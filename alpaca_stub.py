from agents import Portfolio, Trade

class AlpacaStub:
    def __init__(self, cash=100_000):
        self.cash = cash
        self.holdings = {}

    def get_portfolio(self):
        total = self.cash + sum(self.holdings.values())
        return Portfolio(self.cash, self.holdings.copy(), total)

    def submit_trade(self, trade: Trade):
        if trade.side == "BUY" and self.cash >= trade.amount:
            self.cash -= trade.amount
            self.holdings[trade.symbol] = self.holdings.get(trade.symbol, 0) + trade.amount
        elif trade.side == "SELL":
            owned = self.holdings.get(trade.symbol, 0)
            sell = min(owned, trade.amount)
            self.cash += sell
            self.holdings[trade.symbol] = owned - sell
