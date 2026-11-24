import unittest
from unittest.mock import AsyncMock
from uuid import uuid4
from character_storage import CharacterStorage
from character_memory import CharacterMemory
from character_vectors import SemanticRecall, normalize

class VectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_semantic_and_scope(self):
        conn=AsyncMock(); cid=uuid4(); storage=CharacterStorage(conn,cid)
        conn.fetch.side_effect=[[dict(id=1,content='猫咪',layer=1)], [dict(id=1,content='猫咪',embedding=None)]]
        semantic=SemanticRecall(AsyncMock(),'https://example.com/v1','key','model',2)
        semantic.embed=AsyncMock(side_effect=[[[1,0]],[[1,0]]])
        self.assertEqual([r['id'] for r in await CharacterMemory(storage,semantic).recall('宠物')],[1])
        self.assertTrue(all(c.args[1]==cid for c in conn.fetch.call_args_list))
        self.assertEqual(conn.execute.call_args.args[1:3],(cid,1))
    async def test_fallback(self):
        conn=AsyncMock(); conn.fetch.return_value=[dict(id=1,content='apple',layer=1)]
        semantic=AsyncMock(); semantic.scores.side_effect=RuntimeError()
        self.assertEqual(len(await CharacterMemory(CharacterStorage(conn,uuid4()),semantic).recall('apple')),1)
    def test_invalid_vectors(self):
        for v in ([0,0],[float('nan'),1],[1],['1',2]):
            with self.assertRaises(ValueError): normalize(v,2)
