from flask import Flask, jsonify, request
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from confluent_kafka import Producer
import os
import json
import time

# Import unserer neuen Module
from models.volatility_surface import SVIVolatilitySurface
from models.option_pricer import OptionPricer
from data.mock_market_data import MockMarketData

app = Flask(__name__)

# Kafka Producer
p = Producer({'bootstrap.servers': os.getenv('REDPANDA', 'redpanda:9092')})

# Prometheus Metrics
REQS = Counter('http_requests_total', 'Total HTTP requests', ['endpoint'])

# Initialize Options Pricing Models
vol_surface = SVIVolatilitySurface()
option_pricer = OptionPricer(vol_surface)
market_data = MockMarketData()

def send_event(topic, event):
    p.produce(topic, json.dumps(event).encode('utf-8'))
    p.flush()

# ==================== Original Endpoints ====================

@app.route('/options')
def list_options():
    REQS.labels(endpoint='/options').inc()
    return jsonify([
        {"id": "OPT-001", "strike": 120, "type": "call"},
        {"id": "OPT-002", "strike": 80, "type": "put"},
        {"id": "OPT-003", "strike": 70, "type": "call"}
    ])

@app.route('/trade', methods=['POST'])
def trade():
    REQS.labels(endpoint='/trade').inc()
    data = request.json or {}
    event = {"time": int(time.time()), "action": "trade", "payload": data}
    send_event("trades", event)
    return jsonify({"status": "sent", "event": event})

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# ==================== New Options Pricing Endpoints ====================

@app.route('/api/underlyings')
def get_underlyings():
    """Liste aller verfügbaren Underlyings"""
    REQS.labels(endpoint='/api/underlyings').inc()
    return jsonify(market_data.get_underlyings())

@app.route('/api/volatility-surface')
def get_volatility_surface():
    """
    Volatility Surface für gegebenes Underlying
    Query params: ?symbol=DAX
    """
    REQS.labels(endpoint='/api/volatility-surface').inc()
    
    symbol = request.args.get('symbol', 'DAX')
    
    # Hole Spot Price für Symbol
    underlyings = market_data.get_underlyings()
    underlying = next((u for u in underlyings if u['symbol'] == symbol), None)
    
    if not underlying:
        return jsonify({"error": "Unknown underlying"}), 404
    
    spot = underlying['spot']
    rate = market_data.get_risk_free_rate()
    
    # Generiere Surface
    surface = vol_surface.generate_surface(spot=spot, rate=rate)
    
    return jsonify({
        "symbol": symbol,
        "spot": spot,
        "surface": surface
    })

@app.route('/api/option-chain')
def get_option_chain():
    """
    Option Chain für gegebenes Underlying mit Preisen
    Query params: ?symbol=DAX
    """
    REQS.labels(endpoint='/api/option-chain').inc()
    
    symbol = request.args.get('symbol', 'DAX')
    
    # Hole Underlying Info
    underlyings = market_data.get_underlyings()
    underlying = next((u for u in underlyings if u['symbol'] == symbol), None)
    
    if not underlying:
        return jsonify({"error": "Unknown underlying"}), 404
    
    spot = underlying['spot']
    rate = market_data.get_risk_free_rate()
    
    # Generiere Option Chain
    options = market_data.generate_option_chain(symbol, spot)
    
    # Berechne Preise und Greeks für jede Option
    for opt in options:
        price = option_pricer.black_scholes_price(
            spot=spot,
            strike=opt['strike'],
            time_to_maturity=opt['maturity'],
            rate=rate,
            option_type=opt['type']
        )
        
        greeks = option_pricer.calculate_greeks(
            spot=spot,
            strike=opt['strike'],
            time_to_maturity=opt['maturity'],
            rate=rate,
            option_type=opt['type']
        )
        
        # Hole Implied Vol
        impl_vol = vol_surface.implied_volatility(
            opt['strike'], spot, opt['maturity'], rate
        )
        
        opt['price'] = price
        opt['implied_vol'] = float(impl_vol)
        opt['greeks'] = greeks
    
    return jsonify({
        "symbol": symbol,
        "spot": spot,
        "rate": rate,
        "options": options
    })

@app.route('/api/price-option', methods=['POST'])
def price_option():
    """
    Berechnet Preis und Greeks für einzelne Option
    Body: {
        "symbol": "DAX",
        "strike": 15500,
        "maturity": 0.5,
        "option_type": "call"
    }
    """
    REQS.labels(endpoint='/api/price-option').inc()
    
    data = request.json
    symbol = data.get('symbol', 'DAX')
    strike = float(data.get('strike'))
    maturity = float(data.get('maturity'))
    option_type = data.get('option_type', 'call')
    
    # Hole Underlying Info
    underlyings = market_data.get_underlyings()
    underlying = next((u for u in underlyings if u['symbol'] == symbol), None)
    
    if not underlying:
        return jsonify({"error": "Unknown underlying"}), 404
    
    spot = underlying['spot']
    rate = market_data.get_risk_free_rate()
    
    # Berechne Preis
    price = option_pricer.black_scholes_price(
        spot=spot,
        strike=strike,
        time_to_maturity=maturity,
        rate=rate,
        option_type=option_type
    )
    
    # Berechne Greeks
    greeks = option_pricer.calculate_greeks(
        spot=spot,
        strike=strike,
        time_to_maturity=maturity,
        rate=rate,
        option_type=option_type
    )
    
    # Hole Implied Vol
    impl_vol = vol_surface.implied_volatility(strike, spot, maturity, rate)
    
    # Event an Kafka senden
    event = {
        "time": int(time.time()),
        "action": "price_calculation",
        "payload": {
            "symbol": symbol,
            "strike": strike,
            "maturity": maturity,
            "option_type": option_type,
            "price": price
        }
    }
    send_event("pricing", event)
    
    return jsonify({
        "symbol": symbol,
        "spot": spot,
        "strike": strike,
        "maturity": maturity,
        "option_type": option_type,
        "price": price,
        "implied_vol": float(impl_vol),
        "greeks": greeks,
        "rate": rate
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)