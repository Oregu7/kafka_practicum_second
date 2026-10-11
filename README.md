# Фильтр сообщений (Faust)

`messages` → блокировка → цензура → `filtered_messages`.

## Топики и таблицы

Топики Kafka: `messages`, `blocked_users`, `filtered_messages`. Число партиций у всех топиков и таблиц
задаёт константа `PARTITIONS` (3) в `app.py`; таблица должна совпадать по партициям с топиком,
из которого она пишется.

| Таблица | Содержимое | Заполняется |
|---|---|---|
| `blocked_users_table` | `user_id` → список заблокированных (`default=list`) | агентом из топика `blocked_users` |
| `stop_words_table` | `GlobalTable`: стоп-слово → `True` (`default=bool`, `use_partitioner=True`) | через HTTP воркера |

Обе таблицы персистентны: Faust хранит их в служебных changelog-топиках.

## Как это работает

* `blocked_users` — события блокировки; в список заблокированных можно только добавлять.
* Агент `filter_messages`: `stream.filter` отбрасывает сообщения от заблокированных отправителей, затем процессор
  `censor_stop_words` заменяет стоп-слова звёздочками (без учёта регистра, только целые слова), результат уходит в
  `filtered_messages`.
* Стоп-слова меняются на лету через HTTP, перезапуск не нужен.
* Ключ сообщения в `messages` должен быть `recipient_id`, в `blocked_users` — `user_id`
  (иначе блокировка окажется в чужой партиции). `client.py` ставит ключи сам.
* Стоп-слова лежат в `GlobalTable`: полный список есть у каждого воркера, поэтому цензура и `GET /stop-words/`
  работают одинаково на любом воркере.

## HTTP (воркер, порт 6066)

| Запрос | Что делает |
|---|---|
| `GET /blocked-users/{user_id}/` | список заблокированных пользователем |
| `POST /blocked-users/{user_id}/{target_id}/` | `user_id` блокирует `target_id`; ответ `202`, команда уходит в топик `blocked_users` и применяется агентом асинхронно |
| `GET /stop-words/` | список стоп-слов |
| `POST /stop-words/{word}/` | добавить стоп-слово, в ответе обновлённый список |
| `DELETE /stop-words/{word}/` | убрать стоп-слово, в ответе обновлённый список |
| `GET /docs` | Swagger UI: описание и пробные запросы к эндпоинтам |
| `GET /docs/swagger.json` | OpenAPI-спецификация (её читает Swagger UI) |

Swagger UI даёт библиотека [`aiohttp-swagger`](https://pypi.org/project/aiohttp-swagger/): `http://127.0.0.1:6066/docs`.
Статика UI лежит внутри пакета, интернет не нужен. Библиотека подключается к aiohttp-приложению веб-сервера Faust
через хук `app.on_webserver_init` в `endpoints.py`.
Спецификация описана вручную в `openapi.yaml` — при добавлении или изменении эндпоинтов обновляйте его.

## Файлы

* `app.py` — приложение, топики, таблицы и агенты;
* `endpoints.py` — HTTP-эндпоинты и подключение Swagger (подключается через `autodiscover`);
* `openapi.yaml` — OpenAPI-спецификация эндпоинтов;
* `utils.py` — вспомогательные функции (цензура, нормализация слова);
* `client.py` — проверка: отправка сообщений, блокировки, стоп-слова, чтение топика;
* `docker-compose.yml` — три брокера Kafka, приложение `app` и Kafka UI (`http://127.0.0.1:8080`);
* `Dockerfile` — образ приложения (`app.py`, `endpoints.py`, `openapi.yaml`, `utils.py`, зависимости из `requirements.txt`).

## Запуск

Всё в Docker (брокеры + воркер Faust):
```
docker compose up -d --build
docker compose logs -f app
```
Адрес брокеров в контейнере берётся из переменной `KAFKA_BROKER` (в compose — внутренние адреса
`kafka-N:9092`). HTTP воркера доступен на хосте: `http://127.0.0.1:6066`. Если брокеры ещё не готовы,
контейнер `app` перезапустится сам (`restart: on-failure`).

Пересобрать после правок кода: `docker compose up -d --build app`.

### Воркер локально (Windows)

Брокеры в Docker, воркер на хосте (без `KAFKA_BROKER` используются адреса `127.0.0.1:9092/9095/9096`):
```
docker compose up -d kafka-0 kafka-1 kafka-2
set PYTHONUTF8=1
.venv\Scripts\python -m faust -A app worker -l info
```
Контейнер `app` при этом не запускайте — он занимает порт 6066.

При самом первом старте воркер мог не увидеть только что созданные топики и не получить
партиции — тогда перезапустите его один раз.

Если топики уже создавались с другим числом партиций, Faust выдаст ошибку о несовпадении — пересоздайте их
(`docker compose down -v`, затем запуск заново).

## Проверка

```
python client.py block bob alice          # bob блокирует alice
python client.py send alice bob "hi"      # отброшено
python client.py ban плохо                # слово маскируется: *****
python client.py send carol bob "это плохо"
python client.py read filtered_messages
python client.py unban плохо              # убрать стоп-слово
curl http://127.0.0.1:6066/stop-words/
curl -X POST http://127.0.0.1:6066/blocked-users/bob/alice/   # то же, что client.py block bob alice
curl http://127.0.0.1:6066/blocked-users/bob/
```
