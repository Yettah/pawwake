"""Dashboard-only character administration."""
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
import auth, shared, character_registry as registry
from character_gateway import enabled
from character_storage import CharacterStorage
from character_security import tenant_scope
from character_maintenance import CharacterMaintenance
from db.core import get_pool

router = APIRouter(prefix='/dashboard/characters')

def guard(request):
    if not auth.valid_dashboard_session(request.cookies.get(shared.DASHBOARD_SESSION_COOKIE, '')):
        raise HTTPException(401, 'Dashboard login required')
    if request.method != 'GET' and not auth.request_has_same_origin(request):
        raise HTTPException(403, 'Origin rejected')
    if not enabled() or not shared.DATABASE_ENABLED:
        raise HTTPException(503, 'Multi-character database disabled')

@router.get('', response_class=HTMLResponse)
async def page(request: Request):
    guard(request)
    return shared.templates.TemplateResponse(request, 'characters.html', {}, headers={'Cache-Control':'no-store'})

@router.get('/data')
async def listing(request: Request):
    guard(request)
    async with (await get_pool()).acquire() as c:
        rows = await c.fetch('SELECT id,name,system_prompt FROM multi_characters ORDER BY created_at')
    return JSONResponse([dict(id=str(r['id']),name=r['name'],system_prompt=r['system_prompt']) for r in rows],headers={'Cache-Control':'no-store'})

@router.post('/data')
async def create(request: Request):
    guard(request)
    body = await request.json()
    name, prompt = fields(body)
    async with (await get_pool()).acquire() as c:
        cid,key = await registry.create_character(c,name,prompt)
    return JSONResponse({'id':str(cid),'key':key},headers={'Cache-Control':'no-store'})

def fields(body):
    if not isinstance(body,dict): raise HTTPException(400,'Invalid body')
    name,prompt=body.get('name'),body.get('system_prompt','')
    if not isinstance(name,str) or not 1<=len(name.strip())<=120 or not isinstance(prompt,str) or len(prompt)>50000:
        raise HTTPException(400,'Invalid name or prompt')
    return name.strip(),prompt

@router.post('/{cid}/edit')
async def edit(cid: UUID, request: Request):
    guard(request)
    name,prompt=fields(await request.json())
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            if not await c.fetchval('UPDATE multi_characters SET name=$2,system_prompt=$3 WHERE id=$1 RETURNING id',cid,name,prompt): raise HTTPException(404,'Unknown character')
    return {'ok':True}

@router.post('/{cid}/rotate')
async def rotate(cid: UUID, request: Request):
    guard(request)
    key=registry.new_key()
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            async with c.transaction():
                if not await c.fetchval('SELECT id FROM multi_characters WHERE id=$1 FOR UPDATE',cid): raise HTTPException(404,'Unknown character')
                await c.execute('UPDATE multi_character_keys SET revoked_at=now() WHERE character_id=$1 AND revoked_at IS NULL',cid)
                await c.execute('INSERT INTO multi_character_keys(key_digest,character_id) VALUES($1,$2)',registry.digest_key(key),cid)
    return JSONResponse({'key':key},headers={'Cache-Control':'no-store'})

@router.get('/{cid}/details')
async def details(cid: UUID, request: Request):
    guard(request)
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            if not await c.fetchval('SELECT id FROM multi_characters WHERE id=$1',cid): raise HTTPException(404,'Unknown character')
            memories=await c.fetch('SELECT id,content,layer FROM multi_memory WHERE character_id=$1 ORDER BY id DESC LIMIT 100',cid)
            history=await c.fetch('SELECT id,role,content FROM multi_conversation WHERE character_id=$1 ORDER BY id DESC LIMIT 100',cid)
            archive=await c.fetch('SELECT id,content,layer FROM multi_memory_archive WHERE character_id=$1 AND restored_at IS NULL ORDER BY id DESC LIMIT 100',cid)
    return JSONResponse({'memories':[dict(r) for r in memories],'history':[dict(r) for r in history],'archive':[dict(r) for r in archive]},headers={'Cache-Control':'no-store'})

@router.post('/{cid}/restore/{aid}')
async def restore(cid: UUID, aid: int, request: Request):
    guard(request)
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            result=await CharacterMaintenance(CharacterStorage(c,cid)).restore(aid)
    if result is None: raise HTTPException(404,'Archive unavailable')
    return {'id':result}

@router.get('/{cid}/settings')
async def get_settings(cid: UUID, request: Request):
    guard(request)
    from character_settings import load
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            try: result = await load(c,cid)
            except PermissionError: raise HTTPException(404,'Unknown character')
    return JSONResponse(result,headers={'Cache-Control':'no-store'})

@router.post('/{cid}/settings')
async def set_settings(cid: UUID, request: Request):
    guard(request)
    import json
    from character_settings import validate
    try: result=validate(await request.json())
    except ValueError: raise HTTPException(400,'Invalid settings')
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            if not await c.fetchval('UPDATE multi_characters SET settings=$2::jsonb WHERE id=$1 RETURNING id',cid,json.dumps(result)): raise HTTPException(404,'Unknown character')
    return {'ok':True}

@router.get('/{cid}/backup')
async def backup(cid: UUID, request: Request):
    guard(request)
    from character_portability import export_character
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            try: data=await export_character(c,cid)
            except LookupError: raise HTTPException(404,'Unknown character')
    return JSONResponse(data,headers={'Cache-Control':'no-store','Content-Disposition':f'attachment; filename="character-{cid}.json"'})

@router.post('/{cid}/import')
async def import_backup(cid: UUID, request: Request):
    guard(request)
    from character_portability import import_memories
    import json
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>5_000_000: raise HTTPException(413,'Backup too large')
    try:
        body=json.loads(raw)
        if not isinstance(body,dict) or type(body.get('preview')) is not bool: raise ValueError()
        async with (await get_pool()).acquire() as c:
            async with tenant_scope(c,cid):
                return await import_memories(c,cid,body.get('backup'),body['preview'])
    except ValueError: raise HTTPException(400,'Invalid backup')
    except LookupError: raise HTTPException(404,'Unknown character')

@router.post('/{cid}/memory')
async def add_manual_memory(cid: UUID, request: Request):
    guard(request)
    from character_portability import memory_fields
    try: content,layer=memory_fields(await request.json())
    except ValueError: raise HTTPException(400,'Invalid memory')
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            if not await c.fetchval('SELECT id FROM multi_characters WHERE id=$1',cid): raise HTTPException(404,'Unknown character')
            return {'id':await CharacterStorage(c,cid).add_memory(content,layer)}

@router.post('/{cid}/memory/{mid}/edit')
async def edit_manual_memory(cid: UUID, mid: int, request: Request):
    guard(request)
    from character_portability import memory_fields
    try: content,layer=memory_fields(await request.json())
    except ValueError: raise HTTPException(400,'Invalid memory')
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            async with c.transaction():
                if not await c.fetchval('UPDATE multi_memory SET content=$3,layer=$4 WHERE character_id=$1 AND id=$2 AND layer<>1 RETURNING id',cid,mid,content,layer): raise HTTPException(409,'Missing or protected memory')
                await c.execute('DELETE FROM multi_vectors WHERE character_id=$1 AND memory_id=$2',cid,mid)
    return {'ok':True}

@router.post('/{cid}/memory/{mid}/archive')
async def archive_manual_memory(cid: UUID, mid: int, request: Request):
    guard(request)
    async with (await get_pool()).acquire() as c:
        async with tenant_scope(c,cid):
            async with c.transaction():
                row=await c.fetchrow('DELETE FROM multi_memory WHERE character_id=$1 AND id=$2 AND layer<>1 RETURNING content,layer',cid,mid)
                if row is None: raise HTTPException(409,'Missing or protected memory')
                aid=await c.fetchval('INSERT INTO multi_memory_archive(character_id,original_id,content,layer) VALUES($1,$2,$3,$4) RETURNING id',cid,mid,row['content'],row['layer'])
    return {'id':aid}
