"""Stateless character MCP tools. Resolve credentials on every tool call."""
from contextvars import ContextVar
from character_storage import CharacterStorage
from character_memory import CharacterMemory
from character_gateway import session_id

credential_context = ContextVar('character_mcp_key', default=None)

async def execute(conn, key, operation, **args):
    storage = await CharacterStorage.from_key(conn, key)
    from character_security import tenant_scope
    async with tenant_scope(conn, storage._id):
        return await _execute_scoped(conn, storage, operation, **args)

async def _execute_scoped(conn, storage, operation, **args):
    if operation == 'search':
        query, limit = args['query'], args.get('limit', 15)
        if not isinstance(query, str) or not query.strip() or len(query)>4000 or type(limit) is not int or not 1<=limit<=50:
            raise ValueError('invalid search')
        return {'memories': await CharacterMemory(storage).recall(query, limit)}
    if operation == 'read':
        mid = args['memory_id']
        if type(mid) is not int or mid<1: raise ValueError('invalid memory ID')
        row = await conn.fetchrow('SELECT id,content,layer FROM multi_memory WHERE character_id=$1 AND id=$2', storage._id, mid)
        return {'memory': dict(row) if row else None}
    if operation == 'add':
        content, layer = args['content'], args.get('layer', 3)
        if not isinstance(content,str) or not content.strip() or len(content)>4000 or type(layer) is not int or layer not in (2,3):
            raise ValueError('invalid memory; core memories require dashboard')
        return {'id': await storage.add_memory(content.strip(),layer)}
    if operation == 'history':
        rows = await storage.recent_messages(session_id(args.get('session','default')), args.get('limit',20))
        return {'messages': [dict(r) for r in rows]}
    raise ValueError('unsupported operation')

async def call(operation, **args):
    import shared
    from character_gateway import enabled
    from db.core import get_pool
    key = credential_context.get()
    if not key or not enabled() or not shared.DATABASE_ENABLED or not shared.MEMORY_ENABLED:
        raise PermissionError('character MCP unavailable')
    async with (await get_pool()).acquire() as conn:
        return await execute(conn,key,operation,**args)


def build_server():
    from mcp.server.mcpserver import MCPServer
    server = MCPServer('Pawwake Character', title='Character Memory', description='Character-scoped memory tools', version='0.1.0')
    @server.tool(description='Search current character memories by keyword.')
    async def search_memory(query: str, limit: int = 15) -> dict:
        return await call('search',query=query,limit=limit)
    @server.tool(description='Read a memory belonging to the current character.')
    async def read_memory(memory_id: int) -> dict:
        return await call('read',memory_id=memory_id)
    @server.tool(description='Append event or fragment memory; core memories are dashboard-only.')
    async def add_memory(content: str, layer: int = 3) -> dict:
        return await call('add',content=content,layer=layer)
    @server.tool(description='Read recent messages in a current-character session.')
    async def recent_history(session: str = 'default', limit: int = 20) -> dict:
        return await call('history',session=session,limit=limit)
    return server

class CharacterMCPAuth:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        from starlette.responses import JSONResponse
        from starlette.requests import Request
        from character_gateway import credential, enabled
        import shared
        from db.core import get_pool
        from character_registry import resolve_character
        if scope['type'] != 'http':
            return await self.app(scope,receive,send)
        key = credential(Request(scope))
        if not enabled() or not shared.DATABASE_ENABLED or not shared.MEMORY_ENABLED:
            return await JSONResponse({'error':'unavailable'},503)(scope,receive,send)
        if not key:
            return await JSONResponse({'error':'unauthorized'},401)(scope,receive,send)
        async with (await get_pool()).acquire() as conn:
            valid = await resolve_character(conn,key)
        if valid is None:
            return await JSONResponse({'error':'unauthorized'},401)(scope,receive,send)
        token = credential_context.set(key)
        try:
            await self.app(scope,receive,send)
        finally:
            credential_context.reset(token)
