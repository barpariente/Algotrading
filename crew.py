import os
from crewai import Agent, Crew, Process
from tools import StockPriceTool, RiskValidationTool, TradeCalculatorTool
from tasks import trend_task, news_task, decision_task, risk_task

def create_crew():
    # 1. Trend Analyst (Technical)
    trend_analyst = Agent(
        role='Trend Analyst',
        goal='Identify price trends for PLTR, NFLX, and PLTK using historical closing prices.',
        backstory='You are a master of technical analysis. You look for patterns and RSI levels.',
        tools=[StockPriceTool()], 
        verbose=True,
        allow_delegation=False
    )

    # 2. News Analyst (Sentiment)
    news_analyst = Agent(
        role='News Analyst',
        goal='Analyze recent headlines and sentiment for PLTR, NFLX, and PLTK.',
        backstory='Former financial journalist. You identify if news is bullish or bearish.',
        verbose=True,
        allow_delegation=False
    )

    # 3. Decision Maker (Portfolio Manager)
    decision_maker = Agent(
        role='Decision Maker',
        goal='Synthesize technical and sentiment data to propose specific buy/sell trades.',
        backstory='You balance technical trends and news to make high-conviction trade ideas.',
        tools=[TradeCalculatorTool()], 
        verbose=True,
        allow_delegation=False
    )

    # 4. Risk Manager (Gatekeeper)
    risk_manager = Agent(
        role='Risk Manager',
        goal='Validate proposed trades against 30% exposure and 20% cash limits.',
        backstory='You are a strict risk officer. You check every trade against the risk_validator.',
        tools=[RiskValidationTool()], 
        verbose=True,
        allow_delegation=False
    )
    
    t1 = trend_task(trend_analyst)
    t2 = news_task(news_analyst)
    t3 = decision_task(decision_maker, [t1, t2])
    t4 = risk_task(risk_manager)
    return Crew(
        agents=[trend_analyst, news_analyst, risk_manager, decision_maker],
        tasks=[t1, t2, t3, t4],
        process=Process.sequential
    )