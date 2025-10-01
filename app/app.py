from flask import Flask, jsonify, request
from prometheus_client import Counter, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
from confluent_kafka import Producer
import os, json, time
app = Flask(__name__)
p = Producer({'bootstrap.servers': os.getenv('REDPANDA','redpanda:9092')})
REQS = Counter('http_requests_total', 'Total HTTP requests', ['endpoint'])
def send_event(topic,event):
    p.produce(topic, json.dumps(event).encode('utf-8'))
    p.flush()
@app.route('/options')
def list_options(): 
    REQS.labels(endpoint='/options').inc()
    return jsonify([{"id":"OPT-001","strike":120,"type":"call"},
                    {"id":"OPT-002","strike":80,"type":"put"},
                     {"id":"OPT-003","strike":70,"type":"call"}])
@app.route('/trade', methods=['POST'])
def trade(): 
    REQS.labels(endpoint='/trade').inc()
    data = request.json or {}
    event = {"time": int(time.time()), "action":"trade", "payload": data}
    send_event("trades", event)
    return jsonify({"status":"sent", "event": event})
@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=5000)