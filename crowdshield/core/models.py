import datetime
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional

class MarketStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RESOLVED = "RESOLVED"

class BetSide(Enum):
    OVER = "OVER"
    UNDER = "UNDER"

@dataclass
class User:
    id: str
    username: str
    balance: float = 1000.0  # Starting balance for demo

@dataclass
class Bet:
    id: str
    user_id: str
    market_id: str
    side: BetSide
    amount: float
    timestamp: datetime.datetime

@dataclass
class Market:
    id: str
    question: str
    location: str
    threshold_desc: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    status: MarketStatus = MarketStatus.OPEN
    result: Optional[BetSide] = None
    
    # Pools
    pool_over: float = 0.0
    pool_under: float = 0.0
    fee_percent: float = 0.05 # 5% fee
    
    bets: List[Bet] = field(default_factory=list)

    @property
    def total_pool(self) -> float:
        return self.pool_over + self.pool_under

@dataclass
class PreventionFund:
    balance: float = 0.0
    expenses: List[Dict] = field(default_factory=list)
    
    def add_funds(self, amount: float):
        self.balance += amount
        
    def spend(self, amount: float, description: str, recipient: str):
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        self.expenses.append({
            "amount": amount,
            "description": description,
            "recipient": recipient,
            "timestamp": datetime.datetime.now()
        })
