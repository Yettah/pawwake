import unittest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from character_security import tenant_scope, install_policies, TABLES

class SecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_scope_local(self):
        c=MagicMock(); c.execute=AsyncMock(); cid=uuid4()
        async with tenant_scope(c,cid):
            c.execute.assert_awaited_once_with("SELECT set_config('pawwake.character_id', $1, true)",str(cid))
        c.transaction.return_value.__aexit__.assert_awaited_once()
    async def test_invalid_scope(self):
        c=MagicMock()
        with self.assertRaises(ValueError):
            async with tenant_scope(c,'bad'): pass
        c.transaction.assert_not_called()
    async def test_bypass_role_rejected(self):
        c=AsyncMock(); c.fetchval.return_value=True
        with self.assertRaises(RuntimeError): await install_policies(c)
        c.execute.assert_not_called()
    async def test_policy_coverage(self):
        c=AsyncMock(); c.fetchval.return_value=False
        await install_policies(c)
        sql='\n'.join(x.args[0] for x in c.execute.await_args_list)
        for table in TABLES:
            self.assertIn(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY',sql)
        self.assertEqual(sql.count('WITH CHECK (character_id::text'),len(TABLES))
