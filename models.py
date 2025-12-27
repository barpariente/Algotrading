
@dataclass
class Portfolio:
    cash: float
    holdings: Dict[str, float]
    total_value: float


@dataclass
class Trade:
    symbol: str
    side: Literal["BUY", "SELL"]
    amount: float


@dataclass
class RiskDecision:
    symbol: str
    side: Literal["BUY", "SELL"]
    approved: bool
    final_amount: float
    reason: str


@dataclass
class Signal:
    symbol: str
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float

@dataclass
class RateLimitConfig:
    per_second: int
    per_hour: int
    per_day: int
