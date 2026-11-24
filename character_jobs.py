"""Durable per-character extraction jobs; no credentials stored in queue."""
import asyncio
import logging
from uuid import uuid4
from character_security import tenant_scope
from character_storage import CharacterStorage
from character_memory import CharacterMemory

DDL = '''CREATE TABLE IF NOT EXISTS multi_jobs (
 character_id UUID NOT NULL REFERENCES multi_characters(id) ON DELETE CASCADE,
 id UUID NOT NULL, session_id TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','running','done','failed')),
 available_at TIMESTAMPTZ NOT NULL DEFAULT now(), lease UUID,
 PRIMARY KEY(character_id,id));
CREATE INDEX IF NOT EXISTS multi_jobs_ready ON multi_jobs(character_id,state,available_at);'''

async def enqueue(conn,cid,session):
    await conn.execute('INSERT INTO multi_jobs(character_id,id,session_id) VALUES($1,$2,$3)',cid,uuid4(),session)

async def claim(conn,cid):
    return await conn.fetchrow('''UPDATE multi_jobs SET state='running', attempts=attempts+1,
      lease=$2, available_at=now()+interval '5 minutes' WHERE character_id=$1 AND id=(
      SELECT id FROM multi_jobs WHERE character_id=$1 AND state IN ('pending','running')
      AND available_at<=now() AND attempts<5 ORDER BY available_at,id FOR UPDATE SKIP LOCKED LIMIT 1)
      RETURNING id,session_id,lease,attempts''',cid,uuid4())

async def finish(conn,cid,job,success):
    await conn.execute('''UPDATE multi_jobs SET state=CASE WHEN $4 THEN 'done' WHEN attempts>=5 THEN 'failed' ELSE 'pending' END,
      lease=NULL, available_at=now()+interval '30 seconds'*attempts
      WHERE character_id=$1 AND id=$2 AND lease=$3 AND state='running' ''',cid,job['id'],job['lease'],success)

async def process_one(pool,cid,adapter_factory):
    async with pool.acquire() as conn:
        async with tenant_scope(conn,cid):
            await conn.execute("UPDATE multi_jobs SET state='failed',lease=NULL WHERE character_id=$1 AND state='running' AND attempts>=5 AND available_at<=now()",cid)
            job=await claim(conn,cid)
    if not job: return False
    try:
        async with pool.acquire() as conn:
            async with tenant_scope(conn,cid):
                # Lock the leased job through extraction and commit atomically with its writes.
                valid=await conn.fetchval("SELECT 1 FROM multi_jobs WHERE character_id=$1 AND id=$2 AND lease=$3 AND state='running' FOR UPDATE",cid,job['id'],job['lease'])
                if not valid: return False
                adapter=await adapter_factory(conn,cid)
                if adapter is not None:
                    await CharacterMemory(CharacterStorage(conn,cid)).extract_session(job['session_id'],adapter)
                await finish(conn,cid,job,True)
    except Exception:
        logging.getLogger(__name__).warning('Character extraction job failed; retry scheduled')
        async with pool.acquire() as conn:
            async with tenant_scope(conn,cid):
                await finish(conn,cid,job,False)
    return True

async def worker(pool,adapter_factory):
    while True:
        try:
            async with pool.acquire() as conn:
                ids=await conn.fetch('SELECT id FROM multi_characters ORDER BY id')
            for row in ids:
                await process_one(pool,row['id'],adapter_factory)
        except Exception:
            logging.getLogger(__name__).warning('Character job polling failed')
        await asyncio.sleep(5)

async def configured_adapter(conn,cid):
    import os, httpx, shared
    from character_settings import load
    from character_gateway import extract_with_model
    settings=await load(conn,cid)
    if not settings.get('memory_enabled',shared.MEMORY_ENABLED) or not settings.get('extraction_enabled',True): return None
    model=settings.get('memory_model',os.getenv('MEMORY_MODEL',''))
    key=shared.MEMORY_API_KEY or shared.API_KEY
    if not model or not key: raise RuntimeError('extraction configuration unavailable')
    async def adapter(messages,candidates):
        async with httpx.AsyncClient(timeout=60) as client:
            return await asyncio.wait_for(extract_with_model(client,shared.API_BASE_URL,key,model,messages,candidates),timeout=90)
    return adapter
