import json
import logging
import os

from confluent_kafka import Consumer, KafkaException

CONSUMER_CONFIG = {
    "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092,127.0.0.1:9095,127.0.0.1:9096"),
    "group.id": "messages-consumer",
    "auto.offset.reset": "earliest",
}
TOPIC = "filtered_messages"

log = logging.getLogger("MessagesConsumer")


def main():
    consumer = Consumer(CONSUMER_CONFIG)
    consumer.subscribe([TOPIC])
    try:
        while True:
            try:
                msg = consumer.poll(1)
                if msg is None:
                    continue
                if msg.error():
                    log.error("Kafka error: %s", msg.error())
                    continue
                try:
                    log.info("Received: recipient=%s message=%s", msg.key().decode(), json.loads(msg.value()))
                except (ValueError, AttributeError) as exc:
                    log.error("Deserialization failed: %s", exc)
            except KafkaException as exc:
                log.error("Consumer error: %s", exc)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
