import unittest
from unittest.mock import AsyncMock, MagicMock
from character_registry import create_character, resolve_character, revoke_key, digest_key, new_key

class RegistryTests(unittest.IsolatedAsyncioTestCase):
    def conn(self):
        c = MagicMock()
        c.execute = AsyncMock()
        c.fetchval = AsyncMock()
        return c
    async def test_create(self):
        c = self.conn()
        cid, key = await create_character(c, ' A ', 'persona')
        self.assertEqual(len(key), 50)
        self.assertEqual(c.execute.call_args_list[0].args[1:], (cid, 'A', 'persona'))
        self.assertEqual(c.execute.call_args_list[1].args[1:], (digest_key(key), cid))
    async def test_invalid_name(self):
        c = self.conn()
        with self.assertRaises(ValueError): await create_character(c, ' ')
        c.execute.assert_not_called()
    async def test_invalid_key(self):
        c = self.conn()
        self.assertIsNone(await resolve_character(c, 'bad'))
        c.fetchval.assert_not_called()
    async def test_lookup(self):
        c = self.conn(); key = new_key()
        await resolve_character(c, key)
        self.assertIn('revoked_at IS NULL', c.fetchval.call_args.args[0])
        self.assertEqual(c.fetchval.call_args.args[1], digest_key(key))
    async def test_revoke(self):
        c = self.conn(); key = new_key()
        await revoke_key(c, key)
        self.assertEqual(c.execute.call_args.args[1], digest_key(key))
    def test_unique(self):
        self.assertNotEqual(new_key(), new_key())
