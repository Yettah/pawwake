"""Transaction-scoped tenant guard. Registry tables remain administrator-only at app layer."""
from contextlib import asynccontextmanager
from uuid import UUID

TABLES = ('multi_memory','multi_memory_archive','multi_vectors','multi_conversation','multi_cache','multi_jobs')

@asynccontextmanager
async def tenant_scope(conn, cid):
    if not isinstance(cid, UUID):
        raise ValueError('invalid tenant')
    async with conn.transaction():
        await conn.execute("SELECT set_config('pawwake.character_id', $1, true)", str(cid))
        yield conn

async def install_policies(conn):
    # Fixed identifiers only. FORCE also covers ordinary table owners, not BYPASSRLS roles.
    if await conn.fetchval('SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user'):
        raise RuntimeError('RLS requires a non-superuser role without BYPASSRLS')
    for table in TABLES:
        await conn.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        await conn.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
        await conn.execute(f'DROP POLICY IF EXISTS multi_tenant_guard ON {table}')
        await conn.execute(f'''CREATE POLICY multi_tenant_guard ON {table} AS RESTRICTIVE FOR ALL TO PUBLIC
            USING (character_id::text = current_setting('pawwake.character_id', true))
            WITH CHECK (character_id::text = current_setting('pawwake.character_id', true))''')
        await conn.execute(f'DROP POLICY IF EXISTS multi_tenant_access ON {table}')
        await conn.execute(f'CREATE POLICY multi_tenant_access ON {table} FOR ALL TO PUBLIC USING (true) WITH CHECK (true)')
