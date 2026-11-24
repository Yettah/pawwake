import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from character_mcp import execute

class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_scope(self):
        conn=AsyncMock(); conn.transaction=MagicMock(); cid=uuid4(); conn.fetchrow.return_value=None
        with patch('character_storage.resolve_character',return_value=cid):
            self.assertEqual(await execute(conn,'key','read',memory_id=5),{'memory':None})
        self.assertEqual(conn.fetchrow.call_args.args[1:],(cid,5))
    async def test_invalid_key(self):
        conn=AsyncMock(); conn.transaction=MagicMock()
        with patch('character_storage.resolve_character',return_value=None):
            with self.assertRaises(PermissionError): await execute(conn,'key','read',memory_id=5)
        conn.fetchrow.assert_not_called()
    async def test_core_write_denied(self):
        conn=AsyncMock(); conn.transaction=MagicMock()
        with patch('character_storage.resolve_character',return_value=uuid4()):
            with self.assertRaises(ValueError): await execute(conn,'key','add',content='test',layer=1)
        conn.fetchval.assert_not_called()
    async def test_history_scope(self):
        conn=AsyncMock(); conn.transaction=MagicMock(); cid=uuid4(); conn.fetch.return_value=[]
        with patch('character_storage.resolve_character',return_value=cid):
            await execute(conn,'key','history',session='test',limit=5)
        self.assertEqual(conn.fetch.call_args.args[1:],(cid,'test',5))
