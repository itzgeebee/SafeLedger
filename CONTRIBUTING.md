# Contributing to SafeLedger

First off, thank you for considering contributing to SafeLedger! It's people like you that make SafeLedger such a great tool.

SafeLedger is built on principles of **correctness, consistency, and audibility**. We value quality and stability over feature breadth.

## How Can I Contribute?

### Reporting Bugs
- **Check for duplicates**: Before opening a new issue, please search the [Issues](https://github.com/itzgeebee/SafeLedger/issues) to see if it has already been reported.
- **Be descriptive**: Include your OS, Python version, and a clear set of steps to reproduce the bug.
- **Provide Logs**: Attach any relevant error logs or tracebacks.

### Suggesting Enhancements
- **Open an Issue**: Use the issue tracker to describe your proposed change and why it’s useful.
- **Discuss first**: For large changes, please wait for feedback from maintainers before starting implementation to ensure alignment with project goals.

## Your First Code Contribution

### Development Environment Setup
1.  **Fork and Clone**: Fork the repository and clone it locally.
2.  **Internal Dependencies**: We use `pyproject.toml` for dependency management.
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
    ```
3.  **Install Pre-commit Hooks**: We enforce high standards via automated hooks.
    ```bash
    pre-commit install
    ```

## Style & Standards

### Python Code Style
- We follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
- **Formatters**: We use `Black`.
- **Linters**: We use `Ruff` for linting and import sorting.
- **Prerequisite**: Your code must pass `pre-commit run --all-files` before submission.

### Security First
- Always run `Bandit` (included in pre-commit) to scan for common security vulnerabilities.
- Financial data should never be logged in plaintext (use masked values if necessary).
- Never use floating-point types for currency; always use `Decimal`.

### Architecture
SafeLedger follows a **Modular Monolith** pattern. Respect the boundaries:
- **Routers**: HTTP concerns only.
- **Services**: Business logic orchestration.
- **Domain**: Pure business rules and invariants.
- **Repositories**: Data access and persistence.

## Testing Requirements

We take testing very seriously. No code will be merged without appropriate test coverage.
- **Hermetic Isolation**: Tests must run against an isolated database. We use session-scoped schemas to prevent pollution.
- **Idempotency**: All new state-changing endpoints must demonstrate idempotency.
- **Run tests**:
    ```bash
    pytest app/tests/
    ```

## Pull Request Process

1.  **Branching**: Create a feature branch from `main`. Use descriptive names like `feature/add-multi-currency` or `fix/jwt-expiration`.
2.  **Atomic Commits**: Keep your commits small and focused.
3.  **Update Documentation**: If you change an API or add a feature, update the `README.md` and related documentation.
4.  **Rebase**: Before submitting, rebase your branch on top of `main`.
5.  **Review**: Once you submit a PR, maintainers will review it for correctness and style.

## Commit Messages

We recommend following the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` for a new feature.
- `fix:` for a bug fix.
- `docs:` for documentation changes.
- `refactor:` for code changes that neither fix a bug nor add a feature.

Thank you for contributing!
