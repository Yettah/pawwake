import unittest
import asyncio
import sys
import types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Exercise the actual middleware with isolated configuration, no database.
shared = types.ModuleType('shared')
shared.GATEWAY_SECRET = 'test-key'
shared.DASHBOARD_PASSWORD = 'test-password'
shared.SESSION_SECRET = 'x' * 32
shared.DASHBOARD_SESSION_COOKIE = '__Host-pawwake_dashboard_session'
sys.modules['shared'] = shared
import auth
from starlette.requests import Request
from starlette.responses import Response

class AuthTest(unittest.TestCase):
    def check(self, path, key, expected, method='GET'):
        request = Request({'type':'http','path':path,'method':method,'headers':[(b'authorization', ('Bearer '+key).encode())]})
        async def next_call(request): return Response(status_code=204)
        result = asyncio.run(auth.gateway_auth_middleware(request, next_call))
        self.assertEqual(result.status_code, expected)
    def test_chat(self): self.check('/v1/chat/completions','test-key',204,'POST')
    def test_models(self): self.check('/v1/models','test-key',204)
    def test_wrong_key(self): self.check('/v1/chat/completions','wrong',401,'POST')
    def test_dashboard(self): self.check('/api/settings','test-key',401)
    def test_write(self): self.check('/api/memories','test-key',401,'POST')
if __name__ == '__main__': unittest.main()
