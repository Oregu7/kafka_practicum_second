# Фильтр сообщений (Faust)

Сообщения из топика `messages` проходят блокировку и цензуру и попадают в `filtered_messages`, консьюмер пишет их в лог.

## Запуск

```bash
docker compose up -d --build
docker compose logs -f app        # ждём "Worker: Ready"
```

Поднимаются три брокера Kafka, воркер Faust (`http://127.0.0.1:6066`), консьюмер `messages_consumer` и Kafka UI (`http://127.0.0.1:8080`).
Если брокеры ещё не готовы, `app` перезапустится сам (`restart: on-failure`).

## Сиды

Стоп-слова и блокировки из `seeds/*.json` загружаются через HTTP воркера (нужен запущенный `app`):

```bash
python seeds/load.py
```

## Swagger

`http://127.0.0.1:6066/docs` — описание и пробные запросы к эндпоинтам. Спецификация лежит в `openapi.yaml`,
при изменении эндпоинтов обновляйте её вручную.

## Отправка сообщений

Консольной командой (нужен `confluent-kafka`: `pip install -r requirements.txt`):

```bash
python messages_producer.py carol bob "привет"
python messages_producer.py                      # без аргументов спросит сам
```

Или через ручку:

```bash
curl -X POST http://127.0.0.1:6066/messages/ -H "Content-Type: application/json" \
  -d '{"sender_id": "carol", "recipient_id": "bob", "text": "hi"}'
```

Результат — в логе консьюмера: `docker compose logs -f messages_consumer`.
Кириллицу в теле `curl` на Windows передавайте из файла (`--data-binary @msg.json`): `curl.exe` шлёт её не в UTF-8.

## Классы и файлы

- `app.py` — приложение, топики, таблицы и агенты.
- `endpoints.py` — HTTP-эндпоинты и подключение Swagger.
- `openapi.yaml` — OpenAPI-спецификация.
- `utils.py` — цензура и нормализация слова.
- `messages_producer.py` — консольная команда, отправляет сообщение в `messages`.
- `messages_consumer.py` — читает `filtered_messages` и пишет сообщения в лог.
- `docker-compose.yml`, `Dockerfile` — брокеры, воркер, консьюмер (тот же образ, другая команда), Kafka UI.
- `seeds/` — тестовые стоп-слова и блокировки.

## Как это работает

Топики: `messages`, `blocked_users`, `filtered_messages`. Число партиций задаёт `PARTITIONS` (3) в `app.py`.

| Таблица | Содержимое | Заполняется |
|---|---|---|
| `blocked_users_table` | `user_id` → список заблокированных | агентом из топика `blocked_users` |
| `stop_words_table` | `GlobalTable`: стоп-слово → `True` | через HTTP |

- Агент `filter_messages` отбрасывает сообщения от заблокированного отправителя, заменяет стоп-слова звёздочками
  (без учёта регистра, только целые слова) и отправляет результат в `filtered_messages`.
- Блокировки только добавляются; стоп-слова меняются на лету, перезапуск не нужен.
- Ключ сообщения в `messages` — `recipient_id`, в `blocked_users` — `user_id`, иначе блокировка окажется в чужой партиции.
  Команда и ручки ставят ключи сами.
- Таблицы хранятся в RocksDB и восстанавливаются из changelog-топиков Faust.

## HTTP

| Запрос | Что делает |
|---|---|
| `POST /messages/` | отправить сообщение, тело `{sender_id, recipient_id, text}`, ответ `202` |
| `GET /blocked-users/{user_id}/` | список заблокированных пользователем |
| `POST /blocked-users/{user_id}/` | заблокировать, тело `{target_id}`, ответ `202` |
| `GET /stop-words/` | список стоп-слов |
| `POST /stop-words/{word}/` | добавить стоп-слово |
| `DELETE /stop-words/{word}/` | убрать стоп-слово |

Невалидное тело — `400`.

## Проверка

```bash
curl -X POST http://127.0.0.1:6066/blocked-users/bob/ -H "Content-Type: application/json" -d '{"target_id": "alice"}'
python messages_producer.py alice bob "hi"          # отброшено
curl -X POST http://127.0.0.1:6066/stop-words/spam/
python messages_producer.py carol bob "это spam"    # в логе: "это ****"
docker compose logs -f messages_consumer
curl -X DELETE http://127.0.0.1:6066/stop-words/spam/
```

## Воркер локально (Windows)

Брокеры в Docker, воркер на хосте (без `KAFKA_BROKER` берутся `127.0.0.1:9092/9095/9096`). Контейнер `app` не запускайте — он занимает порт 6066:

```bash
docker compose up -d kafka-0 kafka-1 kafka-2
set PYTHONUTF8=1
.venv\Scripts\python -m faust -A app worker -l info
```

Если при первом старте воркер не получил партиции — перезапустите его. Если топики создавались с другим числом
партиций, Faust выдаст ошибку о несовпадении: `docker compose down -v` и запуск заново.
