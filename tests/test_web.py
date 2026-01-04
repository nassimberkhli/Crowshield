def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"CrowdShield" in response.data

def test_create_market_route(client):
    response = client.post('/create', data={
        'question': 'Will it rain?',
        'location': 'London',
        'threshold': '> 5mm'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Market created successfully" in response.data
    assert b"Will it rain?" in response.data

def test_fund_route(client):
    response = client.get('/fund')
    assert response.status_code == 200
    assert b"Prevention Fund" in response.data
