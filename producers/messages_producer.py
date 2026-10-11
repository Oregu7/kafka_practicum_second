import argparse
import json
import sys

from confluent_kafka import Producer

from config.settings import MESSAGES_TOPIC, PRODUCER_CONFIG


def main():
    parser = argparse.ArgumentParser(description=f"Отправить сообщение в топик {MESSAGES_TOPIC}")
    parser.add_argument("sender_id", nargs="?", help="от кого (без аргументов спросит сам)")
    parser.add_argument("recipient_id", nargs="?", help="кому; он же ключ сообщения")
    parser.add_argument("text", nargs="?", help="текст сообщения")
    args = parser.parse_args()

    try:
        for name, label in (("sender_id", "От кого"), ("recipient_id", "Кому"), ("text", "Текст")):
            while not getattr(args, name):
                setattr(args, name, input(f"{label}: ").strip())
    except (EOFError, KeyboardInterrupt):
        sys.exit("\nотменено")

    delivered = []
    producer = Producer(PRODUCER_CONFIG)
    producer.produce(
        MESSAGES_TOPIC,
        key=args.recipient_id.encode(),
        value=json.dumps(vars(args), ensure_ascii=False).encode(),
        on_delivery=lambda err, msg: delivered.append(err or msg),
    )
    if producer.flush(10) or not delivered:
        sys.exit("не удалось отправить сообщение: таймаут")
    result = delivered[0]
    if not hasattr(result, "partition"):
        sys.exit(f"не удалось отправить сообщение: {result}")
    print(f"отправлено: {MESSAGES_TOPIC} partition={result.partition()} offset={result.offset()}")


if __name__ == "__main__":
    main()
