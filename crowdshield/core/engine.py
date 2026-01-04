import uuid
import datetime
from typing import List, Dict, Optional
from .models import Market, User, Bet, BetSide, MarketStatus, PreventionFund

class CrowdShieldEngine:
    def __init__(self):
        self.markets: Dict[str, Market] = {}
        self.users: Dict[str, User] = {}
        self.fund = PreventionFund()
        
        # Create a demo user
        self.create_user("demo_user", "Demo User")

    def create_user(self, user_id: str, username: str) -> User:
        user = User(id=user_id, username=username)
        self.users[user_id] = user
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def create_market(self, question: str, location: str, threshold: str, 
                      start_time: datetime.datetime, end_time: datetime.datetime) -> Market:
        market_id = str(uuid.uuid4())
        market = Market(
            id=market_id,
            question=question,
            location=location,
            threshold_desc=threshold,
            start_time=start_time,
            end_time=end_time
        )
        self.markets[market_id] = market
        return market

    def get_market(self, market_id: str) -> Optional[Market]:
        return self.markets.get(market_id)
    
    def get_all_markets(self) -> List[Market]:
        return list(self.markets.values())

    def place_bet(self, user_id: str, market_id: str, side: BetSide, amount: float):
        market = self.markets.get(market_id)
        user = self.users.get(user_id)
        
        if not market or not user:
            raise ValueError("Market or User not found")
        
        if market.status != MarketStatus.OPEN:
            raise ValueError("Market is not open for betting")
            
        if user.balance < amount:
            raise ValueError("Insufficient balance")
            
        # Deduct balance
        user.balance -= amount
        
        # Create bet
        bet = Bet(
            id=str(uuid.uuid4()),
            user_id=user_id,
            market_id=market_id,
            side=side,
            amount=amount,
            timestamp=datetime.datetime.now()
        )
        market.bets.append(bet)
        
        # Update pools
        if side == BetSide.OVER:
            market.pool_over += amount
        else:
            market.pool_under += amount
            
        return bet

    def resolve_market(self, market_id: str, result: BetSide):
        market = self.markets.get(market_id)
        if not market:
            raise ValueError("Market not found")
            
        if market.status != MarketStatus.OPEN:
             # In a real app we might allow resolving from CLOSED, but for simplicity:
             pass
        
        market.status = MarketStatus.RESOLVED
        market.result = result
        
        total_pool = market.total_pool
        fee = total_pool * market.fee_percent
        distributable = total_pool - fee
        
        # Add fee to prevention fund
        self.fund.add_funds(fee)
        
        # Calculate payouts
        winning_pool = market.pool_over if result == BetSide.OVER else market.pool_under
        
        if winning_pool > 0:
            for bet in market.bets:
                if bet.side == result:
                    # Proportional payout
                    share = bet.amount / winning_pool
                    payout = share * distributable
                    
                    user = self.users.get(bet.user_id)
                    if user:
                        user.balance += payout
        else:
            # If nobody won, maybe refund or everything goes to fund? 
            # For this demo, let's say everything goes to fund if nobody won the side.
            self.fund.add_funds(distributable)

    def close_market(self, market_id: str):
        market = self.markets.get(market_id)
        if market and market.status == MarketStatus.OPEN:
            market.status = MarketStatus.CLOSED
