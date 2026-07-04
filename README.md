# Task Manager Backend

A production-grade REST API built with **FastAPI**, featuring cookie-based JWT authentication with automatic refresh token rotation, role-based access control, database-backed session revocation, rate limiting, and a fully layered architecture.

This project goes beyond basic CRUD to implement the authentication, authorization, and security patterns used in real production systems — the same class of concerns you'd encounter working on a production backend team.

---

## Features

### Authentication & Session Security
- User signup/login with bcrypt-hashed passwords
- **HttpOnly cookie-based token delivery** — access and refresh tokens are never exposed to client-side JavaScript, closing the XSS token-theft vector that `localStorage`-based auth is vulnerable to
- Short-lived access tokens (15 min) paired with long-lived refresh tokens (7 days)
- **Refresh token rotation**: every time a refresh token is used, it is invalidated and replaced with a new one — a stolen refresh token becomes useless the moment the legitimate user refreshes their session
- **Server-side session revocation**: refresh tokens are hashed (SHA-256) and tracked in the database, so a logout (or detected compromise) immediately invalidates the session — something a stateless-JWT-only design cannot do
- Single active session per user, enforced via upsert-on-login (prevents unbounded growth of refresh token records)
- Explicit logout endpoint that revokes the server-side token record and clears cookies

### Authorization
- Role-based access control (RBAC) via a reusable, class-based `RoleChecker` dependency
- Ownership-based authorization — users can only read, modify, or delete their own resources
- Clear separation between `404` (resource doesn't exist) and `403` (resource exists, access denied)

### API Design
- Full CRUD for tasks, scoped to the authenticated user
- Pagination via `skip`/`limit` query parameters with total count in the response
- Admin-only endpoint to view tasks across all users

### Security Hardening
- Password strength validation (minimum length, uppercase, numeric character requirements)
- Rate limiting on the login endpoint (5 requests/minute per IP) to mitigate brute-force attacks
- Environment-based secrets management — no credentials or keys in source control
- Sensitive fields (password hashes) are stripped from all API responses via Pydantic `response_model`

### Reliability & Observability
- Global exception handler for unhandled errors, preventing internal stack traces from reaching clients
- Custom, reusable exception helpers for domain errors (e.g. resource-not-found)
- Request logging middleware (method, path, response time)
- CORS middleware configured for frontend integration

### Data Layer
- SQLAlchemy ORM with relational models (`User`, `Task`, `RefreshToken`)
- Alembic for version-controlled, reversible database migrations

### Testing
- `pytest` + FastAPI `TestClient` test suite covering auth and task flows
- Isolated test database via dependency overrides and fixtures — tests never touch development data

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | SQLAlchemy ORM (SQLite, portable to PostgreSQL) |
| Migrations | Alembic |
| Auth | JWT (python-jose), bcrypt (passlib), HttpOnly cookies |
| Validation | Pydantic v2 |
| Rate Limiting | SlowAPI |
| Testing | Pytest, httpx |
| Server | Uvicorn |

---

## Project Structure

```
task-manager-backend/
├── main.py                     # App entrypoint — middleware, routers, exception handlers
├── config.py                    # Environment-based settings (pydantic-settings)
├── database.py                   # DB engine, session, and get_db dependency
├── models.py                     # SQLAlchemy models (User, Task, RefreshToken)
│
├── schemas/                      # Pydantic request/response models
│   ├── user_schema.py
│   └── task_schema.py
│
├── auth/
│   ├── auth_security.py          # Hashing, JWT creation/decoding, token hashing
│   └── auth_dependency.py        # get_current_user, RoleChecker
│
├── routers/
│   ├── auth_router.py            # /sign-up, /login, /logout
│   ├── refresh_router.py         # /refresh-token (rotation logic)
│   └── task_router.py            # /tasks CRUD, pagination, admin routes
│
├── exceptions/
│   ├── custom_exception.py
│   └── handlers.py
│
├── alembic/                      # Database migration scripts
├── tests/
│   └── test_main.py
│
├── requirements.txt
└── .env                          # Not committed — see .env.example
```

---

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/moizmalik13588/task-manager-backend.git
cd task-manager-backend
```

### 2. Create a virtual environment
```bash
python -m venv env
source env/bin/activate      # Mac/Linux
env\Scripts\activate         # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the project root:
```
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
DATABASE_URL=sqlite:///./tasks.db
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run database migrations
```bash
alembic upgrade head
```

### 6. Start the server
```bash
uvicorn main:app --reload
```

API available at `http://127.0.0.1:8000`, interactive docs at `http://127.0.0.1:8000/docs`.

> **Note:** Cookies are set with `secure=True`, which requires HTTPS. For local HTTP testing, set `secure=False` in `auth_router.py` and `refresh_router.py`.

---

## Running Tests

```bash
pytest -v
```

---

## API Overview

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/sign-up` | Register a new user | No |
| POST | `/login` | Authenticate; sets `access_token` and `refresh_token` HttpOnly cookies | No |
| POST | `/refresh-token` | Rotates the refresh token and issues a new access token | Cookie (refresh) |
| POST | `/logout` | Revokes the server-side session and clears cookies | Cookie (refresh) |
| GET | `/profile` | Get current user's profile | Yes |
| POST | `/tasks` | Create a task | Yes |
| GET | `/tasks?skip=0&limit=10` | List current user's tasks (paginated) | Yes |
| GET | `/tasks/{task_id}` | Get a specific task | Yes |
| PUT | `/tasks/{task_id}` | Update a task | Yes |
| DELETE | `/tasks/{task_id}` | Delete a task | Yes |
| GET | `/admin/all-tasks` | List all tasks (admin only) | Yes (admin role) |

Full interactive documentation is available via Swagger UI at `/docs`.

---

## Authentication Flow

```
1. POST /sign-up          → account created, password bcrypt-hashed
2. POST /login             → access_token (15 min) + refresh_token (7 days)
                              set as HttpOnly cookies; refresh_token hash
                              stored/updated in the database
3. Authenticated requests  → access_token cookie sent automatically by
                              the browser, verified server-side
4. Access token expires    → client calls POST /refresh-token
5. /refresh-token           → validates refresh_token against the DB record,
                              issues a NEW access_token AND a NEW refresh_token,
                              invalidating the old refresh_token immediately
6. POST /logout             → server-side token record marked revoked,
                              cookies cleared — session is fully terminated
                              on both client and server
```

---

## Key Design Decisions

- **Cookies over `localStorage`**: Storing tokens in `HttpOnly` cookies means client-side JavaScript — including any injected via XSS — cannot read or exfiltrate them. The browser handles attachment to requests automatically.
- **Refresh token rotation**: Rather than treating a refresh token as valid for its entire lifetime, each use invalidates it and issues a replacement. This bounds the damage from a leaked refresh token to a single use.
- **Database-tracked sessions**: JWTs are normally stateless, which means there's no way to revoke one before it expires. Storing a hash of the refresh token server-side reintroduces the ability to revoke sessions on logout or on suspicious activity, without giving up the performance benefits of JWT for access tokens.
- **Upsert on login**: Refresh token records are updated in place per user rather than accumulating a new row per login, keeping the table bounded and enforcing a single active session per user.
- **Layered architecture**: Routing, schemas, security logic, and exception handling are separated into distinct modules, making the codebase easier to navigate, test, and extend.
- **Ownership checks over blanket permissions**: Every task operation verifies the requesting user owns the resource, distinguishing `403` (forbidden) from `404` (not found) rather than collapsing both into a generic error.

---

## Possible Extensions

- Per-device/multi-session support (currently one active session per user by design)
- Redis-backed token store for horizontal scalability
- Refresh token family tracking to detect reuse of a rotated (stolen) token
- CI pipeline running the test suite on every push

---

## Author

**Moiz Malik**
Full-Stack / Backend Developer
[GitHub](https://github.com/moizmalik13588)
