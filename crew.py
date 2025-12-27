from crewai import Crew, Agent, Process
from tasks import trend_task, news_task, decision_task, risk_task


def create_crew():
    trend_agent = Agent(
        role="Trend Analyst",
        goal="Analyze market trends",
        backstory="Expert in technical analysis",
        llm=None,
    )

    news_agent = Agent(
        role="News Analyst",
        goal="Analyze financial news",
        backstory="Expert in market sentiment",
        llm=None,
    )

    decision_agent = Agent(
        role="Decision Maker",
        goal="Decide which trades to propose",
        backstory="Portfolio manager",
        llm=None,
    )

    risk_agent = Agent(
        role="Risk Manager",
        goal="Approve or reject trades",
        backstory="Risk management specialist",
        llm=None,
    )

    return Crew(
        agents=[
            trend_agent,
            news_agent,
            decision_agent,
            risk_agent,
        ],
        tasks=[
            trend_task(trend_agent),
            news_task(news_agent),
            decision_task(decision_agent),
            risk_task(risk_agent),
        ],
        process=Process.sequential,
        manager_llm=None,
        verbose=True,
    )
