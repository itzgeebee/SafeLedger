# SafeLedger
A fintech backend system built with FastAPI (Python) that explores the hard parts of financial systems — correctness, consistency, and failure handling. Designed to reflect real-world fintech constraints rather than idealized CRUD applications.

<!-- CI badges -->
[![CI - Postgres tests](https://github.com/itzgeebee/SafeLedger/actions/workflows/postgres-tests.yml/badge.svg)](https://github.com/itzgeebee/SafeLedger/actions/workflows/postgres-tests.yml)

## Overview

This project is a **production-oriented fintech backend** built with **FastAPI (Python)**. It demonstrates how to design and operate **money-moving systems safely**, with a strong focus on correctness, consistency, and failure handling.

Rather than optimizing for feature breadth, this system prioritizes the *hard parts* of financial software: **ledger design, idempotency, reversals, auditability, and operational safety**.

This repository is intended as an educational and reference implementation of real-world fintech backend principles.

## Core Design Principles

*   **Correctness over cleverness** — boring, explicit logic is preferred.
*   **Consistency over availability** for financial state.
*   **Every operation is auditable**.
*   **Failures are expected**, not exceptional.
*   **Money is never stored as floats** (Uses `Decimal`).
*   **Hermetic test isolation** for deterministic validation.

## Key Features

-   **Double-Entry Ledger**: Immutable source of truth for all financial movements.
-   **Atomic Transfers**: Guaranteed all-or-nothing transactions using ACID properties.
-   **Idempotency Engine**: persistent reservation system to prevent duplicate side effects.
-   **Token Revocation**: full-featured logout mechanism using JWT blacklisting.
-   **Rate Limiting**: Integrated middleware for defense-in-depth protection.
-   **Audit Logging**: Detailed trail for all state-changing operations including actor IP and Request ID.
-   **Modular Monolith**: Clean separation of concerns (Routers, Services, Schemas, Repositories).

## Architecture

This system follows a clean architecture pattern, deliberately avoiding premature microservices while enforcing clear boundaries between concerns.

```
┌────────────────────┐
│      Clients       │
│  (Web / API / Jobs)│
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│    API Layer       │
│  FastAPI Routes    │
│  Validation        │
│  Idempotency       │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   Service Layer    │
│  Orchestration     │
│  Transactions      │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   Domain Layer     │
│  Ledger Logic      │
│  Invariants        │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│ Persistence Layer  │
│  PostgreSQL        │
│  Transactions      │
│  Constraints       │
└────────────────────┘
```

## Getting Started

### Prerequisites
-   **Python 3.11+**
-   **PostgreSQL 15+**
-   **Docker** (optional, for local DB)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/itzgeebee/safeLedger.git
    cd safeLedger
    ```

2.  **Create and activate virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Mac/Linux
    # .venv\Scripts\activate  # Windows
    ```

3.  **Install dependencies**:
    ```bash
    pip install -e ".[dev]"
    ```

4.  **Set up environment variables**:
    ```bash
    cp .env.example .env
    # Update DATABASE_URL in .env if needed
    ```

5.  **Run migrations**:
    ```bash
    alembic upgrade head
    ```

### Running Locally

```bash
uvicorn app.main:app --reload
```
The swagger UI will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Quality & Verification

### Automated Tests
The suite uses a **Hermetic Isolation** pattern:
-   **Session Isolation**: Every test run uses a dedicated schema/database.
-   **Transaction Isolation**: Every individual test case is wrapped in a transaction that rolls back.

Run tests with:
```bash
pytest app/tests/
```

### Pre-commit Hooks
We maintain high standards for code quality and security. Hooks run automatically on every commit:
-   **Formatting**: `Black`
-   **Linting**: `Ruff`
-   **Security**: `Bandit` (Statical analysis for vulnerabilities)

Install hooks manually:
```bash
pre-commit install
```

### E2E Testing
A comprehensive **Postman Collection** is provided at `safeledger_e2e_collection.json`. It includes:
-   Automated JWT extraction and request chaining.
-   Variables for easy testing of transfers, account creation, and health checks.

## Technology Stack

-   **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
-   **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Async)
-   **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
-   **Validation**: [Pydantic v2](https://docs.pydantic.dev/)
-   **Database**: [PostgreSQL](https://www.postgresql.org/)
-   **Security**: `BCrypt` for hashing, `python-jose` for JWT tokens.

## License
MIT License - See the [LICENSE](LICENSE) file for details.

## Author
Built and maintained by **Gideon Balogun** (itzgeebee).
