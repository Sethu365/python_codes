from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'test',
    bootstrap_servers=['192.168.0.141:9092'],
    auto_offset_reset='earliest',
    group_id='my-group'
)

print("Listening...")

for msg in consumer:
    print("Received:", msg.value.decode('utf-8'))
