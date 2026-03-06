# Axiom

AI-powered engagement assistant for EverOps client engagements.

## Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker (for local PostgreSQL)

## Local Setup

```bash
# 1. Install dependencies
poetry install

# 2. Start the database
docker compose up -d

# 3. Apply migrations
poetry run python -m backend.db.migrate

# 4. Load seed data
poetry run python -m backend.db.seed

# 5. Run tests
poetry run pytest
```

## Development

See [CLAUDE.md](./CLAUDE.md) for ways of working, TDD rules, and contribution guidelines.

## Structure

```
axiom/
├── backend/       # Python Lambda handlers, DB schema, tests
│   ├── db/        # Migrations, seeds, migration/seed runners
│   ├── src/       # Application source (covered at 100%)
│   └── tests/     # pytest test suite
├── frontend/      # Frontend shell (future epic)
├── infra/         # Terraform infrastructure (future epic)
└── .github/       # PR templates, CODEOWNERS
```

## Tooling

| Tool | Purpose |
|------|---------|
| Poetry | Dependency management |
| pytest + pytest-cov | Testing and 100% coverage enforcement |
| mypy (strict) | Static type checking |
| ruff | Linting and formatting |
