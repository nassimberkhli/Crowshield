from flask import Flask, render_template, request, redirect, url_for, flash
import datetime
from crowdshield.core.engine import CrowdShieldEngine
from crowdshield.core.models import BetSide

app = Flask(__name__)
app.secret_key = 'supersecretkey' # For flash messages

# Initialize Engine
engine = CrowdShieldEngine()

# Helper to format currency
@app.template_filter('currency')
def currency_filter(value):
    return f"€{value:,.2f}"

@app.route('/')
def index():
    markets = engine.get_all_markets()
    user = engine.get_user("demo_user")
    return render_template('index.html', markets=markets, user=user)

@app.route('/create', methods=['GET', 'POST'])
def create_market():
    if request.method == 'POST':
        question = request.form['question']
        location = request.form['location']
        threshold = request.form['threshold']
        # Simplified time handling for demo
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(days=1)
        
        engine.create_market(question, location, threshold, start_time, end_time)
        flash('Market created successfully!')
        return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/market/<market_id>', methods=['GET', 'POST'])
def market_detail(market_id):
    market = engine.get_market(market_id)
    user = engine.get_user("demo_user")
    
    if not market:
        return "Market not found", 404
        
    if request.method == 'POST':
        side_str = request.form['side']
        amount = float(request.form['amount'])
        side = BetSide.OVER if side_str == 'OVER' else BetSide.UNDER
        
        try:
            engine.place_bet(user.id, market.id, side, amount)
            flash(f'Bet placed on {side.value}!')
        except ValueError as e:
            flash(str(e), 'error')
            
        return redirect(url_for('market_detail', market_id=market_id))
        
    return render_template('market.html', market=market, user=user)

@app.route('/resolve/<market_id>', methods=['POST'])
def resolve_market(market_id):
    result_str = request.form['result']
    result = BetSide.OVER if result_str == 'OVER' else BetSide.UNDER
    engine.resolve_market(market_id, result)
    flash(f'Market resolved as {result.value}!')
    return redirect(url_for('market_detail', market_id=market_id))

@app.route('/fund')
def fund_dashboard():
    return render_template('fund.html', fund=engine.fund)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
