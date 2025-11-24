from kafka import KafkaConsumer
import json

# Make sure Kafka is running on this machine at 192.168.0.245:9092

consumer = KafkaConsumer(
    'unified-monitor',                     # Topic name
    bootstrap_servers=['192.168.0.245:9092'],
    auto_offset_reset='latest',            # Read new incoming messages only
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)

print("\n[Kafka Consumer] Listening to topic: unified-monitor\n")

for msg in consumer:
    print("====================================")
    print("New Event Received:")
    print(json.dumps(msg.value, indent=2))
    print("====================================\n")