import datetime
import pytest
from crowdshield.core.models import BetSide, MarketStatus

def test_create_market(engine):
    start = datetime.datetime.now()
    end = start + datetime.timedelta(hours=2)
    market = engine.create_market("Test Question", "Test Loc", "Test Threshold", start, end)
    
    assert market.id is not None
    assert market.status == MarketStatus.OPEN
    assert len(engine.get_all_markets()) == 1

def test_place_bet(engine):
    start = datetime.datetime.now()
    end = start + datetime.timedelta(hours=2)
    market = engine.create_market("Test Q", "Loc", "Thresh", start, end)
    user = engine.create_user("u1", "User 1")
    
    bet = engine.place_bet(user.id, market.id, BetSide.OVER, 100.0)
    
    assert bet.amount == 100.0
    assert user.balance == 900.0
    assert market.pool_over == 100.0
    assert market.total_pool == 100.0

def test_resolve_market_payout(engine):
    # Setup
    start = datetime.datetime.now()
    end = start + datetime.timedelta(hours=2)
    market = engine.create_market("Test Q", "Loc", "Thresh", start, end)
    
    u1 = engine.create_user("u1", "User 1") # Bets 100 on OVER
    u2 = engine.create_user("u2", "User 2") # Bets 100 on UNDER
    
    engine.place_bet(u1.id, market.id, BetSide.OVER, 100.0)
    engine.place_bet(u2.id, market.id, BetSide.UNDER, 100.0)
    
    # Total Pool = 200
    # Fee (5%) = 10
    # Distributable = 190
    
    # Resolve OVER
    engine.resolve_market(market.id, BetSide.OVER)
    
    assert market.status == MarketStatus.RESOLVED
    assert engine.fund.balance == 10.0
    
    # u1 should get 190 (all distributable since they are the only winner)
    # u1 started with 1000, bet 100 -> 900. Won 190 -> 1090.
    assert u1.balance == 1090.0
    
    # u2 lost everything. 1000 - 100 = 900.
    assert u2.balance == 900.0

def test_insufficient_funds(engine):
    start = datetime.datetime.now()
    end = start + datetime.timedelta(hours=2)
    market = engine.create_market("Test Q", "Loc", "Thresh", start, end)
    user = engine.create_user("u1", "User 1")
    user.balance = 50.0
    
    with pytest.raises(ValueError):
        engine.place_bet(user.id, market.id, BetSide.OVER, 100.0)
