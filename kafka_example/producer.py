from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['192.168.0.245:9092'],
)

while True:
    msg = input("Enter message: ")
    producer.send('test', msg.encode('utf-8'))
    producer.flush()
    print("Sent:", msg)
