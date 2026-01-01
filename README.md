# SafeLedger
A fintech backend system built with FastAPI (Python) that explores the hard parts of financial systems — correctness, consistency, and failure handling.  Designed to reflect real-world fintech constraints rather than idealised CRUD applications.

# Fintech Backend System (FastAPI)

## Overview

This project is a **production-oriented fintech backend** built with **FastAPI (Python)**. It demonstrates how to design and operate **money-moving systems safely**, with a strong focus on correctness, consistency, and failure handling.

Rather than optimising for feature breadth, this system prioritises the *hard parts* of financial software: **ledger design, idempotency, reversals, auditability, and operational safety**.

This repository is intended as an educational and reference implementation of real-world fintech backend principles.

---

## Core Design Principles

* **Correctness over cleverness** — boring, explicit logic is preferred
* **Consistency over availability** for financial state
* **Every operation is auditable**
* **Failures are expected**, not exceptional
* **Money is never stored as floats**

---

## What This Project Is

* A reference implementation of a **wallet & ledger-based financial system**
* A demonstration of **industry-grade backend design decisions**
* A platform for exploring **failure modes in payment systems**

## What This Project Is NOT

* A full banking product
* A UI-focused application
* A replacement for licensed financial infrastructure

---

## System Capabilities

### Ledger & Wallets

* Double-entry ledger system
* Accounts and balances derived from immutable entries
* Support for credits, debits, reversals, and adjustments
* Full audit trail for all financial movements

### Idempotent APIs

* Idempotency keys for all state-changing operations
* Safe retry behaviour for clients and webhooks
* Protection against duplicate requests

### Payments & Transfers

* Internal transfers between wallets
* External payment flow simulation
* Asynchronous processing for non-blocking operations

### Failure Handling

* Graceful handling of partial failures
* Retry-safe background jobs
* Explicit state transitions

### Observability

* Structured logging
* Clear error boundaries
* Operational visibility into financial flows

---

## Architecture Overview

High-level components:

* **API Layer** — FastAPI endpoints with explicit contracts
* **Domain Layer** — Ledger, wallets, and business rules
* **Persistence Layer** — PostgreSQL with transactional guarantees
* **Async Workers** — Background processing for retries and reconciliation

The system is designed to be deployed in a **cloud-native environment** (e.g. AWS), but avoids unnecessary complexity.

---

## Data Model Philosophy

* Financial state is derived, not stored
* Ledger entries are immutable
* Balances are calculated from entries
* Every change has a reason and a source

This approach ensures:

* Traceability
* Easier debugging
* Regulatory friendliness

---

## Technology Stack

* **Language:** Python 3.x
* **Framework:** FastAPI
* **Database:** PostgreSQL
* **Async Processing:** Background workers / task queue
* **Infrastructure:** AWS-friendly (EC2/ECS/RDS compatible)

---

## Getting Started

### Prerequisites

* Python 3.10+
* PostgreSQL
* Virtual environment tool (venv, poetry, etc.)

### Installation

```bash
# Clone the repository
git clone https://github.com/itzgeebee/SafeLedger.git
cd SafeLedger

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Start the application
uvicorn app.main:app --reload
```

---

## Example Use Cases

* Building a wallet service
* Understanding ledger-based accounting systems
* Designing idempotent APIs
* Studying fintech failure modes
* Preparing for fintech system design interviews

---

## Tradeoffs & Decisions

This project intentionally:

* Avoids microservices sprawl
* Favors explicit logic over abstractions
* Accepts stricter constraints to preserve correctness

These tradeoffs mirror real-world financial system design.

---

## Roadmap

Planned additions:

* Reconciliation jobs
* Webhook simulation
* Multi-currency support
* Improved metrics and alerting
* Go-based service comparison (experimental)

---

## Disclaimer

This project is **for educational purposes only**. It does not handle real money and should not be used in production environments without appropriate licensing, security reviews, and compliance checks.

---

## Author

Built and maintained by a backend engineer focused on **fintech systems, reliability, and financial correctness**.

---

## License

MIT License
