# Storely 🏪

> AI-powered inventory management system for small Uzbek retail shops.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Django](https://img.shields.io/badge/Django-6.0-green)](https://djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.x-red)](https://django-rest-framework.org)
[![Tests](https://img.shields.io/badge/Tests-31%20passed-brightgreen)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📌 Problem

Small retail shops in Uzbekistan still manage inventory
with paper notebooks:
- Data gets lost or damaged
- No search, no statistics
- Debt tracking is manual and unreliable
- No alerts when stock runs low

**Storely** replaces the notebook with an intelligent system
accessible via Telegram — no app installation required.

---

## ✨ Features

- 📦 **Inventory management** — products, variants, stock levels
- 💰 **Sales tracking** — cash, card, or credit sales
- 💳 **Debt management** — track who owes what, process payments
- 📊 **Reports** — daily and monthly summaries
- ⚠️ **Low stock alerts** — automatic Telegram notifications
- 🎤 **Voice input** — speak in Uzbek, Storely understands
- 🖼️ **Image recognition** — photograph a product to log a sale
- 🤖 **Telegram bot** — full control without a web interface
- 🏪 **Multi-store** — one account, multiple shops

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.x + Django REST Framework |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 |
| Background tasks | Celery + Celery Beat |
| Telegram bot | aiogram 3.x |
| Voice recognition | OpenAI Whisper API |
| Image recognition | OpenAI GPT-4o Vision |
| Containerization | Docker + docker-compose |
| Web server | Nginx + Gunicorn |
| Testing | pytest + pytest-django |

---

## 🏗 Architecture

```
storely/
├── apps/
│   ├── stores/        # Store model and management
│   ├── inventory/     # Products, variants, categories
│   ├── sales/         # Sales and sale items
│   ├── customers/     # Customer management
│   ├── debts/         # Debt tracking and payments
│   ├── reports/       # Daily and monthly reports
│   ├── notifications/ # Celery tasks and alerts
│   └── bot/           # Telegram bot (aiogram)
│       ├── routers/   # start, sale, stock, debt, report, voice, image
│       ├── services/  # whisper, parser, vision
│       └── middlewares/
├── core/              # BaseModel, permissions, pagination
├── config/            # Django settings, URLs, Celery
├── docker/            # Dockerfiles, Nginx config
├── scripts/           # Startup scripts
└── tests/             # 31 tests
```

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone git@github.com:OktamTurgun/storely.git
cd storely
```

### 2. Environment

```bash
cp .env.example .env
# .env faylini to'ldiring
```

### 3. Docker bilan ishga tushirish

```bash
docker-compose up --build
```

### 4. Superuser yaratish

```bash
docker-compose exec django python manage.py createsuperuser
```

### 5. API

```
http://localhost:8000/api/v1/
http://localhost:8000/admin/
```

---

## 🔌 API Endpoints

### Stores
```
GET    /api/v1/stores/
POST   /api/v1/stores/
GET    /api/v1/stores/{id}/
PUT    /api/v1/stores/{id}/
DELETE /api/v1/stores/{id}/
```

### Inventory
```
GET    /api/v1/stores/{store_id}/products/
POST   /api/v1/stores/{store_id}/products/
GET    /api/v1/stores/{store_id}/products/low-stock/
POST   /api/v1/variants/restock/
```

### Sales
```
GET    /api/v1/stores/{store_id}/sales/
POST   /api/v1/stores/sales/create/
GET    /api/v1/sales/{id}/
```

### Debts
```
GET    /api/v1/stores/{store_id}/debts/
POST   /api/v1/debts/{id}/pay/
```

### Reports
```
GET    /api/v1/stores/{store_id}/reports/today/
GET    /api/v1/stores/{store_id}/reports/monthly/?year=2026&month=6
```

---

## 🤖 Telegram Bot

| Action | How |
|---|---|
| Daily report | "📊 Bugungi hisobot" |
| Low stock | "⚠️ Kam qolganlar" |
| Debt list | "💳 Qarz" |
| Pay debt | "✅ To'lash" |
| Log sale | 📷 Photo of product |
| Any action | 🎤 Voice message in Uzbek |

### Voice examples
```
"Non 10 dona sotdim"      → logs sale
"5 qop un keldi"          → restocks inventory
"Sardor 50000 qarzga"     → creates debt
"Bugungi statistika"      → sends report
```

---

## 🧪 Tests

```bash
pytest
```

```
31 passed in 44.34s ✅
```

| Module | Tests |
|---|---|
| Inventory models | 5 |
| Inventory services | 6 |
| Sales services | 6 |
| Debt services | 4 |
| Sales views | 5 |
| Bot parser | 5 |

---

## 🔑 Environment Variables

```env
SECRET_KEY=
DEBUG=
ALLOWED_HOSTS=

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

REDIS_URL=

TELEGRAM_BOT_TOKEN=
OPENAI_API_KEY=
SENTRY_DSN=
```

---

## 📄 License

MIT © [Uktam Turgunov](https://github.com/OktamTurgun)
