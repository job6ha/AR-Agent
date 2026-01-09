# AGENTS.md

## Scope
Use this file as the entry point for agent guidance in this repo.

## Key docs
- Backend architecture: `AGENT_DOC/BACKEND.md`
- Frontend structure: `AGENT_DOC/FRONTEND.md`
- Testing rules: `AGENT_DOC/TESTING.md`

## Project layout (current)
- Backend entrypoint: `backend/main.py`
- Backend layers: `backend/api`, `backend/services`, `backend/schemas`, `backend/domain`
- Core domain package: `backend/domain/kaeri_ar_agent`
- Frontend entrypoint: `frontend/src/App.svelte`
- Frontend features: `frontend/src/lib/features`

## Conventions
- Keep backend controller thin; push orchestration to services and pure logic to domain.
- Frontend: keep `routes`/entry thin; put feature logic in `lib/features/<feature>`.
- Avoid adding cross-feature utilities to shared until reuse is clear.

## Testing (backend)
- Follow the rules in `AGENT_DOC/TESTING.md`.
- Prefer unit tests for domain, use-case tests for services, and API contract tests for controllers.
