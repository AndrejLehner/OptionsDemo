from flask import Flask, jsonify, request
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from confluent_kafka import Producer
import os, json, time

app = Flask(__name__)

# -----------------------------------------------------------
# 1. Kafka/Redpanda Konfiguration
# Stellt den Producer her, der 'redpanda:9092' als Standard verwendet.
# Dies nutzt den Docker-Servicenamen (DNS-Auflösung innerhalb des Containers).
p = Producer({'bootstrap.servers': os.getenv('REDPANDA', 'redpanda:9092')})

def send_event(topic, event):
    """Sendet ein JSON-Event asynchron an den Kafka/Redpanda-Broker."""
    p.produce(topic, json.dumps(event).encode('utf-8'))
    p.flush(timeout=1) # Blockiert kurz, um die Nachricht zu senden

# -----------------------------------------------------------
# 2. Prometheus Metriken
# Definiert einen Zähler für alle HTTP-Anfragen, etikettiert nach Endpunkt.
REQS = Counter('http_requests_total', 'Total HTTP requests count', ['endpoint'])

# -----------------------------------------------------------
# 3. HTTP Endpunkte

@app.route('/options', methods=['GET'])
def list_options():
    """Listet verfügbare Optionsscheine auf und zählt die Anfrage."""
    REQS.labels(endpoint='/options').inc()
    return jsonify([
        {"id":"OPT-001", "name": "Tesla Call", "strike": 120, "type": "call", "price": 5.20},
        {"id":"OPT-002", "name": "Apple Put", "strike": 80, "type": "put", "price": 3.45}
    ])

@app.route('/trade', methods=['POST'])
def trade():
    """Nimmt einen Trade-Post entgegen und publiziert ihn an das Kafka-Thema 'trades'."""
    REQS.labels(endpoint='/trade').inc()
    
    # Sicherstellen, dass die Daten JSON sind
    data = request.json or {}
    
    if not data or 'id' not in data or 'qty' not in data:
        return jsonify({"status": "error", "message": "Missing 'id' or 'qty' in request."}), 400

    # Event-Payload erstellen
    event = {
        "time": int(time.time() * 1000), # Millisekunden-Zeitstempel
        "action": "trade_executed",
        "payload": data
    }
    
    # Event senden
    try:
        send_event("trades", event)
        # Für das Logging in Promtail/Loki:
        app.logger.info(f"Trade event published for ID: {data['id']} with qty: {data['qty']}")
        return jsonify({"status":"sent", "event": event, "message": "Trade event published to Redpanda."})
    except Exception as e:
        app.logger.error(f"Failed to publish trade event: {e}")
        return jsonify({"status": "error", "message": "Failed to connect to Kafka/Redpanda."}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Exponiert die Prometheus-Metriken."""
    # Gibt die gesammelten Metriken zurück (einschließlich http_requests_total)
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


# -----------------------------------------------------------
# 4. App Start
if __name__ == '__main__':
    # 'host=0.0.0.0' ist wichtig, damit die App innerhalb des Docker-Containers erreichbar ist.
    app.run(host='0.0.0.0', port=5000)