Техническое задание: Разработка сервиса управления заказами

### 1. Введение

Разработать сервис управления заказами на FastAPI, поддерживающий аутентификацию, работу с очередями сообщений, кеширование и фоновую обработку задач.

### 2. Функциональные требования

#### 2.1 API эндпоинты

|       |                         |                                          |
| ----- | ----------------------- | ---------------------------------------- |
| Метод | URL                     | Описание                                 |
| POST  | /register/              | Регистрация пользователя (email, пароль) |
| POST  | /token/                 | Получение JWT-токена (OAuth2)            |
| POST  | /orders/                | Создание заказа (Только авторизованные)  |
| GET   | /orders/{order_id}/     | Получение заказа (сначала из Redis)      |
| PATCH | /orders/{order_id}/     | Обновление статуса заказа                |
| GET   | /orders/user/{user_id}/ | Получение заказов пользователя           |

#### 2.2 База данных (PostgreSQL)

Таблица orders:

- id (UUID, primary key)
- user_id (int, ForeignKey на пользователей)
- items (JSON, список товаров)
- total_price (float)
- status (enum: PENDING, PAID, SHIPPED, CANCELED)
- created_at (datetime)

### 2.3 Очереди сообщений (Kafka + Outbox Pattern)

- Kafka используется как event-bus между сервисами (Celery не является брокером событий).
- При создании заказа сервис записывает заказ и `OutboxEvent` в PostgreSQL в рамках одной транзакции (таблица `outbox_events`).
- Фоновый `OutboxPublisherService` (запускается внутри `api` на lifespan, если `ENABLE_OUTBOX_PUBLISHER=true`) публикует события из `outbox_events` в Kafka topic `order-events`.
- Publisher публикует только записи со `status=PENDING` и когда `next_attempt_at <= now()`.
- После успешной отправки запись переводится в `status=SENT`.
- При ошибке отправки Publisher увеличивает `attempts`, выставляет `next_attempt_at` по exponential backoff и повторяет попытку до `OUTBOX_MAX_ATTEMPTS`.
- После исчерпания попыток Publisher отправляет данные события в DLQ topic `order-events-dlq` и переводит запись в `status=FAILED`.
- Отдельный `consumer` подписывается на `order-events`, валидирует envelope и запускает Celery task `process_order` (передает как минимум `order_id` и `event_id`).
- Невалидные сообщения (ошибки валидации envelope в `consumer`) отправляются в `order-events-dlq` с причиной.

#### 2.4 Redis (Кеширование заказов)

- Если заказ запрашивается повторно – отдавать его из кеша (TTL = 5 минут).
- При изменении заказа – обновлять кеш.

#### 2.5 Celery (Фоновая обработка)

- Фоновая задача обработки заказа (в демо реализации: `time.sleep(2)` и `print(f"Order {order_id} processed")`).

#### 2.6 Безопасность

- JWT-аутентификация (OAuth2 Password Flow).
- CORS-защита (ограничение кросс-доменных запросов).
- Rate limiting (ограничение частоты запросов на API).
- SQL-инъекции – только ORM-запросы.

### 3. Нефункциональные требования

- Использование FastAPI с Pydantic.
- Работа с PostgreSQL через SQLAlchemy + Alembic.
- Асинхронное взаимодействие с Kafka.
- Docker Compose для развертывания всей инфраструктуры.
- Код должен быть структурированным и документированным.

### 4. Инструкция по сдаче

1. Разместить код на GitHub / GitLab.
2. Описать установку и запуск в README.md.
3. Прислать ссылку на репозиторий.
4. Обязателен SwaggerUI

5. Критерии приёмки:

– работоспособность всех API, описанных в ТЗ

– корректная авторизация и защита эндпоинтов

– реальная работа Redis, брокера сообщений и фоновых задач

– возможность развернуть проект через docker-compose

– наличие и актуальность Swagger и README.md

– соответствие реализации бизнес-сценариям, описанным в ТЗ

– корректная обработка ошибок и возврат соответствующих HTTP-статусов

– соблюдение заявленного технологического стека

– отсутствие хардкода чувствительных данных и конфигураций

Запуск приложения через Docker Compose
Требования

## Запуск приложения через Docker Compose

### Требования

На машине должны быть установлены:

- Docker
- Docker Compose

### 1. Клонирование проекта

git clone <repo_url>  
cd order_service

### 2. Подготовка переменных окружения

В файле `.env` указаны тестовые переменные

### 3. Сборка и запуск

Запуск:

docker compose up --build

### 4. Что поднимается

Вместе с приложением запускаются следующие сервисы:

- `api` — FastAPI приложение
- `consumer` — Kafka consumer для обработки событий `order-events`
- `celery_worker` — Celery worker для фоновых задач
- `postgres` — PostgreSQL
- `redis` — Redis для кэширования и broker/result backend для Celery
- `kafka` — Kafka broker
- `kafka-init` — одноразовый контейнер для создания topic
- `kafka-ui` — веб-интерфейс для Kafka

### 5. Доступные адреса

После запуска сервисы будут доступны по адресам:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- Kafka UI: `http://localhost:8070`

### 6. Остановка приложения

docker compose down

---

## Тестирование приложения

### 1. Проверка доступности Swagger

После запуска можно запустить docker compose exec api pytest или пройтись руками:

http://localhost:8000/docs

Через Swagger можно последовательно проверить все основные сценарии.

---

## Базовый сценарий тестирования

### Шаг 1. Регистрация пользователя

`POST /register/`

Пример тела запроса:

{  
 "email": "user@example.com",  
 "password": "strongpassword123"  
}

Ожидаемый результат:

- пользователь успешно создаётся
- возвращается информация о пользователе

---

### Шаг 2. Получение JWT-токена

`POST /token/`

Используется `OAuth2 Password Flow`.

Передай данные формы:

- `username` — email пользователя
- `password` — пароль пользователя

Ожидаемый результат:

- возвращается `access_token`
- тип токена: `bearer`

После этого нажми кнопку **Authorize** в Swagger и вставь токен в формате:

Bearer <access_token>

---

### Шаг 3. Создание заказа

`POST /orders/`

Пример тела запроса:

{  
 "items": [
{
"sku": "SKU-001",
"name": "Product 1",
"qty": 2,
"price": 100
}
],  
}

Ожидаемый результат:

- создаётся заказ
- заказ сохраняется в PostgreSQL
- возвращается объект заказа со статусом `PENDING`
- сервис создает заказ и `OutboxEvent`; затем `OutboxPublisherService` публикует событие `order.created` в Kafka topic `order-events`

---

### Шаг 4. Проверка фоновой обработки

После создания заказа:

- consumer читает сообщение из Kafka
- Celery worker получает задачу
- в логах worker появляется сообщение об обработке заказа

Проверить логи можно так:

docker compose logs -f consumer  
docker compose logs -f celery_worker

Ожидаемый результат в логах worker:

Order <order_id> processed

---

### Шаг 5. Получение заказа по ID

`GET /orders/{order_id}/`

Ожидаемый результат:

- заказ успешно возвращается по `order_id`
- при повторном запросе заказ должен браться из Redis cache

---

### Шаг 6. Обновление статуса заказа

`PATCH /orders/{order_id}/`

Пример тела запроса:

{  
 "status": "PAID"  
}

Ожидаемый результат:

- статус заказа изменяется
- обновлённый заказ возвращается в ответе
- кэш Redis обновляется

---

### Шаг 7. Получение всех заказов пользователя

`GET /orders/user/{user_id}/`

Ожидаемый результат:

- возвращается список всех заказов пользователя

---

## Проверка Kafka

Открой Kafka UI:

http://localhost:8070

Там можно проверить:

- наличие topic `order-events`
- наличие topic `order-events-dlq`
- сообщения, публикуемые при создании заказа (event `order.created`)
- состояние consumer group

---

## Проверка Redis cache

Проверка может выполняться двумя способами:

### По логике приложения

- первый `GET /orders/{id}/` читает заказ из БД
- повторный `GET /orders/{id}/` должен брать заказ из Redis

### Через Redis CLI

Подключение к контейнеру:

docker exec -it order_service_redis redis-cli

Просмотр ключей:

KEYS \*

---

## Проверка базы данных

Подключение к PostgreSQL:

docker exec -it order_service_postgres psql -U postgres -d orders_db

Проверка таблиц:

\dt

Проверка заказов:

SELECT \* FROM orders;

Проверка пользователей:

SELECT \* FROM users;

---

## Просмотр логов

Логи всех сервисов:

docker compose logs -f

Логи отдельного сервиса:

docker compose logs -f api  
docker compose logs -f consumer  
docker compose logs -f celery_worker  
docker compose logs -f kafka
