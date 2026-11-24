import unittest
from unittest.mock import AsyncMock
from uuid import uuid4
from character_storage import CharacterStorage
from character_memory import CharacterMemory

class MemoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = AsyncMock()
        self.a, self.b = uuid4(), uuid4()
        self.rows = {self.a:[dict(id=1,content='喜欢苹果',layer=1)],self.b:[dict(id=2,content='喜欢香蕉',layer=1)]}
        async def fetch(sql,cid,*args):
            if 'multi_conversation' in sql:
                return [dict(id=10,role='user',content='喜欢苹果')] if cid==self.a else []
            return self.rows[cid]
        self.conn.fetch.side_effect=fetch
        self.conn.fetchval.return_value=3
        self.engine=CharacterMemory(CharacterStorage(self.conn,self.a))
    async def test_recall(self):
        self.assertEqual([r['id'] for r in await self.engine.recall('喜欢')],[1])
        self.assertNotIn('香蕉',await self.engine.context('喜欢'))
        self.assertEqual(await CharacterMemory(CharacterStorage(self.conn,self.b)).recall('苹果'),[])
    async def test_extract(self):
        ex=AsyncMock(return_value=[dict(action='add',content='喜欢红苹果',importance=7,source_message_ids=[10]),dict(action='add',content='外部证据',importance=7,source_message_ids=[99]),dict(action='add',content='喜欢苹果',importance=7,source_message_ids=[10])])
        self.assertEqual(await self.engine.extract_session('same',ex),[3])
        self.assertEqual(self.conn.fetchval.call_args.args[1:],(self.a,'喜欢红苹果',2))
        self.assertEqual(ex.call_args.args[1],self.rows[self.a])
    async def test_empty(self):
        ex=AsyncMock()
        self.assertEqual(await CharacterMemory(CharacterStorage(self.conn,self.b)).extract_session('same',ex),[])
        ex.assert_not_called()
    async def test_limit(self):
        with self.assertRaises(ValueError): await self.engine.recall('x',0)
