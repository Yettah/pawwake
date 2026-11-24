"""Run only against a disposable PostgreSQL database, never production."""
import os, unittest
from uuid import uuid4
from character_registry import initialize as registry, create_character, resolve_character
from character_storage import initialize as storage, CharacterStorage
from character_security import tenant_scope, install_policies
from character_jobs import DDL, enqueue, claim, finish

@unittest.skipUnless(os.getenv('PAWWAKE_TEST_DATABASE_URL'), 'disposable PostgreSQL URL not configured')
class PostgresIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_isolation_and_job_recovery(self):
        import asyncpg
        conn = await asyncpg.connect(os.environ['PAWWAKE_TEST_DATABASE_URL'])
        schema = 'pwtest_' + uuid4().hex
        try:
            await conn.execute(f'CREATE SCHEMA {schema}')
            await conn.execute(f'SET search_path TO {schema}')
            await registry(conn); await storage(conn); await conn.execute(DDL)
            await install_policies(conn)
            a, ka = await create_character(conn, 'A')
            b, kb = await create_character(conn, 'B')
            self.assertEqual(await resolve_character(conn, ka), a)
            self.assertEqual(await resolve_character(conn, kb), b)
            async with tenant_scope(conn,a):
                await CharacterStorage(conn,a).add_memory('A only',1)
                await enqueue(conn,a,'default')
                job = await claim(conn,a)
                self.assertIsNotNone(job)
            async with tenant_scope(conn,b):
                await CharacterStorage(conn,b).add_memory('B only',2)
                self.assertEqual(await conn.fetchval('SELECT count(*) FROM multi_memory'),1)
                self.assertEqual(await conn.fetchval('SELECT content FROM multi_memory'),'B only')
                self.assertFalse(await CharacterStorage(conn,a).memories())
                self.assertIsNone(await claim(conn,b))
                with self.assertRaises(asyncpg.PostgresError):
                    async with conn.transaction():
                        await CharacterStorage(conn,a).add_memory('forbidden',3)
            self.assertEqual(await conn.fetchval('SELECT count(*) FROM multi_memory'),0)
            async with tenant_scope(conn,a):
                await conn.execute("UPDATE multi_jobs SET available_at=now()-interval '1 second'")
                recovered = await claim(conn,a)
                self.assertEqual(recovered['id'],job['id'])
                self.assertNotEqual(recovered['lease'],job['lease'])
                await finish(conn,a,job,True)
                self.assertEqual(await conn.fetchval('SELECT state FROM multi_jobs'),'running')
                await finish(conn,a,recovered,True)
                self.assertEqual(await conn.fetchval('SELECT state FROM multi_jobs'),'done')
        finally:
            await conn.execute('RESET search_path')
            await conn.execute(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
            await conn.close()
