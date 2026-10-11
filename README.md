# Фильтр сообщений (Faust)

Сообщения из `messages` проходят блокировку и цензуру и попадают в `filtered_messages`, консьюмер пишет их в лог.

## Запуск

```bash
docker compose up -d --build
docker compose logs -f app        # ждём "Worker: Ready"
```

Поднимаются три брокера Kafka, воркер Faust (`http://127.0.0.1:6066`), консьюмер и Kafka UI (`http://127.0.0.1:8080`).

## Сиды

Стоп-слова и блокировки из `seeds/*.json` (нужен запущенный `app`):

```bash
python seeds/load.py
```

## Swagger

`http://127.0.0.1:6066/docs` — все эндпоинты с пробными запросами. Спецификация — `worker/openapi.yaml`.

## Отправка сообщений

Командой (нужен `pip install -r requirements.txt`):

```bash
python -m producers.messages_producer carol bob "привет"
python -m producers.messages_producer            # без аргументов спросит сам
```

Или через ручку:

```bash
curl -X POST http://127.0.0.1:6066/messages/ -H "Content-Type: application/json" \
  -d '{"sender_id": "carol", "recipient_id": "bob", "text": "hi"}'
```

Результат — в логе консьюмера: `docker compose logs -f messages_consumer`.
Кириллицу в `curl` на Windows передавайте из файла (`--data-binary @msg.json`).

## Файлы

- `config/settings.py` — брокеры (`KAFKA_BOOTSTRAP`), топики, число партиций, конфиги продьюсера и консьюмера.
- `worker/` — Faust-приложение: `app.py` (топики, таблицы), `models.py`, `agents.py`, `endpoints.py`, `utils.py`, `openapi.yaml`.
- `producers/messages_producer.py` — отправляет сообщение в `messages`.
- `consumers/messages_consumer.py` — читает `filtered_messages` и пишет в лог.
- `seeds/` — тестовые стоп-слова и блокировки.

## Как это работает

- Топики: `messages`, `blocked_users`, `filtered_messages`; партиций 3 (`PARTITIONS` в `config/settings.py`).
- Агент `filter_messages` отбрасывает сообщения от заблокированного отправителя и заменяет стоп-слова звёздочками
  (без учёта регистра, только целые слова). Готовое сообщение уходит в `filtered_messages` через sink `send_to_filtered`.
- Блокировки (`blocked_users_table`) заполняет агент из топика `blocked_users`, они только добавляются.
  Стоп-слова (`stop_words_table`, `GlobalTable`) меняются через HTTP на лету.
- Таблицы хранятся в RocksDB и восстанавливаются из changelog-топиков Faust.
- Ключ сообщения — `recipient_id` (в `blocked_users` — `user_id`), иначе блокировка окажется в чужой партиции.
  Команда и ручки ставят ключи сами.

## Проверка

```bash
curl -X POST http://127.0.0.1:6066/blocked-users/bob/ -H "Content-Type: application/json" -d '{"target_id": "alice"}'
python -m producers.messages_producer alice bob "hi"          # отброшено
curl -X POST http://127.0.0.1:6066/stop-words/spam/
python -m producers.messages_producer carol bob "это spam"    # в логе: "это ****"
curl -X DELETE http://127.0.0.1:6066/stop-words/spam/
```