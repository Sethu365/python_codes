from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'test',
    bootstrap_servers=['192.168.0.245:9092'],  
    auto_offset_reset='earliest',
    enable_auto_commit=False
)

for msg in consumer:
    print(f"Offset: {msg.offset}, Message: {msg.value.decode()}")
