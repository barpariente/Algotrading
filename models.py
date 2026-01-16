from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class RateLimitConfig:
    per_second: int
    per_hour: int
    per_day: int


@dataclass
class Portfolio:
    cash: float
    holdings: Dict[str, float]      
    total_value: float


@dataclass
class Signal:
    symbol: str
    action: str          
    confidence: float


@dataclass
class Trade:
    symbol: str
    side: str            
    amount: float        


@dataclass
class RiskDecision:
    symbol: str
    side: str
    approved: bool
    final_amount: float
    reason: str
