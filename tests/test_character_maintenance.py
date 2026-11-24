import unittest
from unittest.mock import AsyncMock
from uuid import uuid4
from character_storage import CharacterStorage
from character_maintenance import CharacterMaintenance

class MaintenanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_protects_core_and_preserves_stronger(self):
        s = CharacterStorage(None, uuid4())
        s.memories = AsyncMock(return_value=[dict(id=i,content=c,layer=l) for i,c,l in [(1,'a',3),(2,'a',2),(3,'b',1),(4,'b',3),(5,'c',2)]])
        self.assertEqual(await CharacterMaintenance(s).preview(), [(2,1)])
    async def test_apply_requires_distinct_ids(self):
        s = CharacterStorage(None, uuid4())
        s.archive_duplicate = AsyncMock()
        with self.assertRaises(ValueError):
            await CharacterMaintenance(s).apply(1,1)
        s.archive_duplicate.assert_not_awaited()
    async def test_restore_delegates(self):
        s = CharacterStorage(None, uuid4())
        s.restore_archived_memory = AsyncMock(return_value=9)
        self.assertEqual(await CharacterMaintenance(s).restore(2),9)
        s.restore_archived_memory.assert_awaited_once_with(2)
