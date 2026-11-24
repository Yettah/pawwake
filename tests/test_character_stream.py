import unittest
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager
from character_gateway import stream_reply, extract_with_model

class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def run_stream(self, lines):
        class Client:
            @asynccontextmanager
            async def stream(self,*args,**kwargs):
                yield self
            status_code=200
            async def aiter_lines(self):
                for line in lines: yield line
        save=AsyncMock()
        output=[x async for x in stream_reply(Client(),'url',{}, {},save)]
        return output,save
    async def test_complete(self):
        output,save=await self.run_stream(['data: {"choices":[{"delta":{"content":"你好"},"finish_reason":null}]}','data: {"choices":[{"delta":{},"finish_reason":"stop"}]}','data: [DONE]'])
        save.assert_awaited_once_with('你好'); self.assertEqual(output[-1],'data: [DONE]\n\n')
    async def test_truncated(self):
        output,save=await self.run_stream(['data: {"choices":[{"delta":{"content":"partial"}}]}'])
        save.assert_not_awaited(); self.assertIn('gateway_error',output[-1])
    async def test_invalid(self):
        output,save=await self.run_stream(['data: [DONE]'])
        save.assert_not_awaited(); self.assertIn('gateway_error',output[-1])
