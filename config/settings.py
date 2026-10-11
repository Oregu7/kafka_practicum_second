import os

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092,127.0.0.1:9095,127.0.0.1:9096")
# Faust принимает брокеры в виде kafka://host:port;kafka://host:port
KAFKA_BROKER = ";".join(f"kafka://{addr}" for addr in KAFKA_BOOTSTRAP.split(","))

MESSAGES_TOPIC = "messages"
BLOCKED_USERS_TOPIC = "blocked_users"
STOP_WORDS_TOPIC = "stop_words"
FILTERED_TOPIC = "filtered_messages"

PARTITIONS = 3
REPLICATION_FACTOR = 3

PRODUCER_CONFIG = {
    "bootstrap.servers": KAFKA_BOOTSTRAP,
}

CONSUMER_CONFIG = {
    "bootstrap.servers": KAFKA_BOOTSTRAP,
    "group.id": "messages-consumer",
    "auto.offset.reset": "earliest",
}
