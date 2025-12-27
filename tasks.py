from crewai import Task
from agents import trend_signals, news_signals, DecisionCoordinatorAgent, RiskManagerAgent
from state import STATE

def trend_task(agent):
    return Task(
        description="Trend analysis",
        agent=agent,
        execute=lambda _: STATE["signals"].extend(trend_signals()),
    )

def news_task(agent):
    return Task(
        description="News analysis",
        agent=agent,
        execute=lambda _: STATE["signals"].extend(news_signals()),
    )

def decision_task(agent):
    def run(_):
        decider = DecisionCoordinatorAgent()
        STATE["trades"] = decider.decide(STATE["signals"], STATE["portfolio"])
    return Task("Decision", agent, execute=run)

def risk_task(agent):
    def run(_):
        risk = RiskManagerAgent()
        STATE["decisions"] = risk.evaluate_trades(
            STATE["portfolio"], STATE["trades"], STATE["trade_history"]
        )
    return Task("Risk", agent, execute=run)
