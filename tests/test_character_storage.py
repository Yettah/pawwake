import unittest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from character_storage import CharacterStorage

class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_scope(self):
        c=MagicMock(); c.fetch=AsyncMock(); c.fetchval=AsyncMock(); c.execute=AsyncMock()
        for cid in (uuid4(),uuid4()):
            s=CharacterStorage(c,cid)
            for method,args,dbmethod in [(s.add_memory,('x',1),c.fetchval),(s.memories,(),c.fetch),(s.delete_memory,(1,),c.execute),(s.append_message,('same','user','x'),c.fetchval),(s.messages,('same',),c.fetch),(s.save_cache,('same',{}),c.execute),(s.load_cache,('same',),c.fetchval)]:
                await method(*args)
                self.assertEqual(dbmethod.call_args.args[1],cid)
                self.assertIn('character_id',dbmethod.call_args.args[0])
    async def test_invalid_key(self):
        c=MagicMock()
        with self.assertRaises(PermissionError): await CharacterStorage.from_key(c,'bad')
    def test_no_default(self):
        with self.assertRaises(ValueError): CharacterStorage(None,None)
