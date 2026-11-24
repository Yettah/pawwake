import unittest
from unittest.mock import AsyncMock
from uuid import uuid4
from character_jobs import enqueue, claim, finish

class JobTests(unittest.IsolatedAsyncioTestCase):
    async def test_enqueue_scoped(self):
        conn=AsyncMock(); cid=uuid4()
        await enqueue(conn,cid,'default')
        self.assertEqual(conn.execute.call_args.args[1],cid)
        self.assertEqual(conn.execute.call_args.args[3],'default')
    async def test_claim_lease(self):
        conn=AsyncMock(); cid=uuid4()
        await claim(conn,cid)
        sql, tenant, lease=conn.fetchrow.call_args.args
        self.assertEqual(tenant,cid)
        self.assertIn('SKIP LOCKED',sql)
        self.assertIn('attempts<5',sql)
    async def test_finish_fenced(self):
        conn=AsyncMock(); cid=uuid4(); job={'id':uuid4(),'lease':uuid4()}
        await finish(conn,cid,job,False)
        sql,*args=conn.execute.call_args.args
        self.assertEqual(args,[cid,job['id'],job['lease'],False])
        self.assertIn('lease=$3',sql)
