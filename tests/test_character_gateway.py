import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from character_gateway import prepare

class GatewayTest(unittest.IsolatedAsyncioTestCase):
    async def test_persona(self):
        conn=AsyncMock(); cid=uuid4(); conn.fetchval.side_effect=[cid,'persona A']; conn.fetch.side_effect=[[{'id':1,'content':'apple A','layer':1}], []]
        actual, body, _=await prepare(conn,'pwchar_'+'x'*43,{'messages':[{'role':'system','content':'wrong persona'},{'role':'user','content':'apple'}]})
        self.assertEqual(actual,cid); self.assertEqual(body['messages'][0]['content'],'persona A'); self.assertIn('apple A',body['messages'][1]['content']); self.assertNotIn('wrong persona',str(body)); self.assertEqual(conn.fetch.call_args.args[1],cid)
    async def test_invalid_key(self):
        conn=AsyncMock(); conn.fetchval.return_value=None
        with self.assertRaises(PermissionError): await prepare(conn,'pwchar_'+'x'*43,{})
        conn.fetch.assert_not_called()
    async def test_stream_accepted(self):
        conn=AsyncMock(); conn.fetchval.side_effect=[uuid4(),'persona']; conn.fetch.return_value=[]
        _,body,_=await prepare(conn,'pwchar_'+'x'*43,{'stream':True,'messages':[{'role':'user','content':'hello'}]})
        self.assertTrue(body['stream'])
