---
status: accepted
---

# Browser SaaS on a modular monolith

## Context

The original product is a Windows-oriented local application: Flask serves a classic JavaScript frontend, SQLite data, uploads, and a fixed local user. The desired product is browser-only, with a Cloudflare frontend and an Ubuntu backend. The two 3,000-line composition files cannot be safely replaced in one release.

## Decision

JobHunter will be maintained as a browser-only SaaS: Cloudflare serves a Vanilla TypeScript/Vite frontend, while an Ubuntu-hosted FastAPI modular monolith owns authenticated business behavior, PostgreSQL data, durable background jobs, and R2 file metadata.

Existing Flask routes remain only as a contract-preserving migration adapter behind the FastAPI application interface. Domains move one at a time without dual writes, and the adapter is removed after all route contracts have migrated. The frontend follows the same rule: classic modules remain compatible while controllers move by domain; event delegation and Vite/ESM are introduced only after domain ownership is stable.

`uv` plus `pyproject.toml` and `uv.lock` are the authoritative Python dependency and runtime contract. PowerShell launchers are legacy convenience tools, not production infrastructure.

## Consequences

- FastAPI is the target framework, not an optional sidecar.
- The WSGI adapter and SQLite are temporary compatibility adapters.
- Production remains blocked until trusted identity, per-user authorization, PostgreSQL, and external object storage are implemented.
- A modular monolith keeps deployment and transactions simple while allowing real domain seams.
- Each migration batch requires behavior-equivalent contract tests before the old route/controller is removed.

## Rejected alternatives

- Permanent Flask extension: retains weak request contracts and global runtime state.
- Big-bang rewrite: creates too much simultaneous behavioral and deployment risk.
- Early microservices: adds network, versioning, observability, and transaction cost before a real scaling or ownership seam exists.

See `docs/PRODUCTION_ARCHITECTURE.md` for the target topology and migration gates.
