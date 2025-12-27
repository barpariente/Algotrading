# crew.py
from crewai import Crew, Agent, Process
from tasks import trend_task, news_task, decision_task, risk_task

def create_crew():
    agents = [
        Agent("Trend", goal="Analyze trends", llm=None),
        Agent("News", goal="Analyze news", llm=None),
        Agent("Decision", goal="Decide trades", llm=None),
        Agent("Risk", goal="Manage risk", llm=None),
    ]

    tasks = [
        trend_task(agents[0]),
        news_task(agents[1]),
        decision_task(agents[2]),
        risk_task(agents[3]),
    ]

    return Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        manager_llm=None,
    )
