import unittest
from unittest.mock import AsyncMock
from uuid import uuid4
from character_gateway import prepare, persist, session_id
from character_settings import validate

class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_history_scope(self):
        conn=AsyncMock(); cid=uuid4(); conn.fetchval.side_effect=[cid,'persona']; conn.fetch.return_value=[]
        _, body, _=await prepare(conn,'pwchar_'+'x'*43,{'session_id':'other','messages':[{'role':'user','content':'hello'}]},session='other')
        self.assertEqual(conn.fetch.call_args.args[1:],(cid,'other',40))
        self.assertNotIn('session_id',body)
    async def test_invalid_session(self):
        for value in ('', '../x', None, 'x'*81):
            with self.assertRaises(ValueError): session_id(value)
    async def test_budget(self):
        self.assertEqual(validate({'history_chars':0}),{'history_chars':0})
        with self.assertRaises(ValueError): validate({'history_chars':24001})
