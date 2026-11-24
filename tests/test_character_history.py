import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from character_storage import CharacterStorage
from character_history import context
from character_gateway import prepare

class HistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_scope_and_dedupe(self):
        conn=AsyncMock(); cid=uuid4()
        conn.fetch.return_value=[{'role':'assistant','content':'old reply'},{'role':'user','content':'already here'}]
        result=await context(CharacterStorage(conn,cid),[{'role':'user','content':'already here'}])
        self.assertIn('old reply',result); self.assertNotIn('already here',result)
        self.assertEqual(conn.fetch.call_args.args[1:],(cid,'default',40))
    async def test_budget(self):
        conn=AsyncMock(); conn.fetch.return_value=[{'role':'user','content':'x'*100}]
        self.assertEqual(await context(CharacterStorage(conn,uuid4()),[],budget=10),'')
    async def test_merge(self):
        conn=AsyncMock(); conn.fetchval.side_effect=[uuid4(),'central']; conn.fetch.return_value=[]
        with patch.dict('os.environ',{'MULTI_PROMPT_MODE':'merge'}):
            _,body,_=await prepare(conn,'pwchar_'+'x'*43,{'messages':[{'role':'system','content':'worldbook'},{'role':'user','content':'hi'}]})
        self.assertEqual(body['messages'][0]['content'],'central'); self.assertIn('worldbook',str(body))
