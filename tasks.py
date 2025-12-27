from crewai import Task
from state import STATE
from models import Signal, Trade, RiskManagerAgent, RiskConfig
from collections import defaultdict
from data_providers import fetch_recent_prices


def trend_task(agent):
    def run(_):
        for symbol in STATE["symbols"]:
            prices = fetch_recent_prices(symbol, days=5)
            if len(prices) < 2:
                continue

            if prices[-1] > prices[0]:
                action = "BUY"
            elif prices[-1] < prices[0]:
                action = "SELL"
            else:
                action = "HOLD"

            STATE["signals"].append(
                Signal(
                    symbol=symbol,
                    action=action,
                    confidence=0.6,
                )
            )

        return STATE["signals"]

    return Task(
        description="Analyze momentum using recent price movement",
        agent=agent,
        execute=run,
    )

def news_task(agent):
    def run(_):
        for symbol in STATE["symbols"]:
            news = STATE["external_data"]["news"].get(symbol)
            if not news:
                continue

            headlines = [
                item.get("title", "").lower()
                for item in news.get("news_results", [])
            ]

            positive = sum("beat" in h or "growth" in h for h in headlines)
            negative = sum("miss" in h or "loss" in h for h in headlines)

            if positive > negative:
                action = "BUY"
            elif negative > positive:
                action = "SELL"
            else:
                action = "HOLD"

            STATE["signals"].append(
                Signal(
                    symbol=symbol,
                    action=action,
                    confidence=0.4,
                )
            )

        return STATE["signals"]

    return Task(
        description="Analyze news sentiment using headline keywords",
        agent=agent,
        execute=run,
    )

def decision_task(agent):
    def run(_):
        votes = defaultdict(int)

        for signal in STATE["signals"]:
            if signal.action == "BUY":
                votes[signal.symbol] += 1
            elif signal.action == "SELL":
                votes[signal.symbol] -= 1

        STATE["trades"] = []

        for symbol, score in votes.items():
            if score >= 2:
                STATE["trades"].append(
                    Trade(symbol=symbol, side="BUY", amount=5_000)
                )
            elif score <= -2:
                STATE["trades"].append(
                    Trade(symbol=symbol, side="SELL", amount=5_000)
                )

        return STATE["trades"]

    return Task(
        description="Combine agent signals using majority voting",
        agent=agent,
        execute=run,
    )


def risk_task(agent):
    def run(_):
        risk_manager = RiskManagerAgent(RiskConfig())

        decisions = risk_manager.evaluate_trades(
            portfolio=STATE["portfolio"],
            trades=STATE["trades"],
            trade_history=STATE["trade_history"],
        )

        STATE["decisions"] = decisions
        STATE["trades_to_execute"] = [
            Trade(d.symbol, d.side, d.final_amount)
            for d in decisions
            if d.approved
        ]

        return decisions

    return Task(
        description="Validate trades against risk constraints",
        agent=agent,
        execute=run,
    )
