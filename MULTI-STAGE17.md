# Stage 17 — release audit candidate (not deployment-ready)
- Multi mode now fails startup when persistence is disabled or database initialization fails.
- Added opt-in real PostgreSQL RLS / key / lease recovery integration test in isolated temporary schema.
- Run: python -m unittest discover -s tests -v
- For integration set PAWWAKE_TEST_DATABASE_URL to a disposable database with CREATE SCHEMA permission and a non-superuser, non-BYPASSRLS role. Never use production.
- Local results: 54 existing tests passed; 1 integration test skipped (no database URL). Python compilation and JS syntax checks passed.
- Blockers: asyncpg and MCP SDK not installed locally; no Docker or PostgreSQL executable. Startup, actual RLS, browser, upstream SSE, MCP and Render recovery unverified.
- Known issues remain: extraction jobs use recent session rather than immutable snapshot; no global concurrent dedupe; partial backup restore; network calls inside transactions. Do not deploy to production or import private memories.
