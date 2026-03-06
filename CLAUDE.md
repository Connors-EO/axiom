# Axiom — Claude Ways of Working

## Project Context

### Two repos, two responsibilities

| Repo | Purpose |
|------|---------|
| `Connors-EO/axiom` | The Axiom application — backend Lambda handlers, database schema, frontend shell, Terraform infrastructure |
| `Connors-EO/solution-accelerator` | Source of truth for EverOps playbooks consumed by Axiom via CAG retrieval |

Axiom is an AI-powered engagement assistant. It guides client engagements through structured phases (P0–P5), using playbooks from `solution-accelerator` as contextual knowledge, and traces every LLM interaction for quality measurement and fine-tuning.

### Reference documents

All implementation decisions must align with these documents (stored in the solution-accelerator repo):

1. **Solution Architecture v2.2** — data model, phase definitions, service domains
2. **Data Observability Guide v1.1** — trace schema, quality metrics, gate criteria
3. **Axiom Infrastructure & Delivery Guide v1.1** — repo structure, tooling standards, deployment approach
4. **EverOps Service Domains** — two-gate domain scoping model

When in doubt, read the doc before writing code.

---

## Epic and Story Flow

For every epic:

1. **Research** — read all relevant reference documents before writing a line of code
2. **Issues** — epic and story issues must exist in GitHub before work begins
3. **Branch** — one branch per story, branched from `main`
4. **TDD** — write failing tests first, confirm red, then implement to green
5. **Review** — push branch, leave for human review; never self-merge

---

## Branch Naming

```
feature/{issue-number}-{short-slug}
```

Examples:
- `feature/5-repo-skeleton`
- `feature/6-db-schema`
- `feature/7-seed-data`

Always branch from `main`. Never branch from another feature branch.

---

## TDD Rules

These are non-negotiable:

1. **Red first** — write the test, run it, confirm it fails before writing implementation code
2. **100% coverage** — `coverageThreshold` is set to 100% for all metrics on `backend/src/**`. It never goes down.
3. **No exceptions** — if a line of code in `backend/src/` exists, it must be exercised by a test
4. **Test files live in `backend/tests/`** mirroring the structure of `backend/src/`

Running tests:
```bash
npm test                # run all tests, no coverage report
npm run test:coverage   # run all tests with coverage enforcement
```

---

## Commit Message Format

All commits must follow Conventional Commits with an issue reference:

```
<type>(<scope>): <description> — closes #<issue>
```

Allowed types: `feat`, `fix`, `docs`, `knowledge`, `infra`, `chore`, `refactor`

Examples:
```
feat(schema): add complete postgres schema with RLS — closes #6
feat(repo): initialize axiom repository skeleton — closes #5
docs(claude): add ways of working document
```

Commit messages are enforced by `commitlint` on this repo.

---

## Never-Do List

- **Never merge** a branch yourself — leave for human review via PR
- **Never reduce coverage** — if a change would drop coverage below 100%, the change is wrong
- **Never commit secrets** — `.env`, API keys, passwords, tokens must never appear in commits
- **Never skip the red step** — if you can't show a failing test before implementation, stop and redo
- **Never use `--force` push** to `main`
- **Never create application logic** in a foundation/schema story
- **Never run migrations directly against production** — always use the migration runner

---

## Environment Assumptions

Local development uses `docker-compose`:

```bash
docker compose up -d    # start postgres:16 on localhost:5432
```

Database: `axiom_dev`, user: `axiom`, password: `axiom`

Environment variables (never committed, stored in `.env`):

```
PGHOST=localhost
PGPORT=5432
PGDATABASE=axiom_dev
PGUSER=axiom
PGPASSWORD=axiom
```

`.env` and `.envrc` are in `.gitignore`. Use `.env.example` for documentation.

Database scripts:
```bash
npm run db:migrate   # apply pending migrations
npm run db:seed      # load seed data (idempotent)
```

---

## Definition of Done

A story is done when ALL of the following are true:

- [ ] All acceptance criteria in the GitHub issue are met
- [ ] `npm test` passes with zero failures
- [ ] `npm run test:coverage` passes at 100% on all metrics
- [ ] Branch is pushed to `origin` and a PR is open (or ready to open)
- [ ] No merge has been performed
- [ ] Commit message references the closing issue number
- [ ] No secrets committed
- [ ] No application logic added beyond the story scope
