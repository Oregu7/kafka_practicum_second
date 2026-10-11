import json
import logging

from confluent_kafka import Consumer, KafkaException

from config.settings import CONSUMER_CONFIG, FILTERED_TOPIC

log = logging.getLogger("MessagesConsumer")


def format_message(msg):
    data = json.loads(msg.value())
    return (f"{data['sender_id']} → {data['recipient_id']}: {data['text']}"
            f"   [{msg.topic()} p{msg.partition()}@{msg.offset()}]")


def main():
    consumer = Consumer(CONSUMER_CONFIG)
    consumer.subscribe([FILTERED_TOPIC])
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
                    log.info(format_message(msg))
                except (ValueError, KeyError, TypeError) as exc:
                    log.error("Deserialization failed: %s", exc)
            except KafkaException as exc:
                log.error("Consumer error: %s", exc)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S")
    main()
