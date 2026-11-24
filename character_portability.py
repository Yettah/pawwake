"""Versioned, credential-free character export and validated additive import."""
from character_settings import validate
import json


def memory_fields(row):
    if not isinstance(row, dict) or set(row) != {'content','layer'}:
        raise ValueError('Invalid memory fields')
    text, layer = row['content'], row['layer']
    if not isinstance(text,str) or not text.strip() or len(text)>50000 or type(layer) is not int or layer not in (1,2,3):
        raise ValueError('Invalid memory')
    return text.strip(),layer


def parse_backup(data):
    if not isinstance(data,dict) or data.get('format')!='pawwake-character' or type(data.get('version')) is not int or data['version']!=1:
        raise ValueError('Unsupported backup')
    rows=data.get('memories')
    if not isinstance(rows,list) or len(rows)>10000:
        raise ValueError('Invalid memory list')
    return list(dict.fromkeys(memory_fields(row) for row in rows))


async def export_character(conn,cid):
    async with conn.transaction(isolation='repeatable_read',readonly=True):
        row=await conn.fetchrow('SELECT name,system_prompt,settings FROM multi_characters WHERE id=$1',cid)
        if row is None: raise LookupError('Unknown character')
        settings=row['settings']
        memories=await conn.fetch('SELECT content,layer FROM multi_memory WHERE character_id=$1 ORDER BY id',cid)
        history=await conn.fetch('SELECT session_id,role,content FROM multi_conversation WHERE character_id=$1 ORDER BY id',cid)
    return dict(format='pawwake-character',version=1,character=dict(id=str(cid),name=row['name'],system_prompt=row['system_prompt'],settings=validate(json.loads(settings) if isinstance(settings,str) else settings)),memories=[dict(r) for r in memories],history=[dict(r) for r in history])


async def import_memories(conn,cid,data,preview=True):
    rows=parse_backup(data)
    async with conn.transaction():
        if not await conn.fetchval('SELECT id FROM multi_characters WHERE id=$1 FOR UPDATE',cid): raise LookupError('Unknown character')
        existing={r['content'].strip() for r in await conn.fetch('SELECT content FROM multi_memory WHERE character_id=$1',cid)}
        pending=[]
        for content,layer in rows:
            if content not in existing:
                pending.append((content,layer)); existing.add(content)
        if not preview:
            for content,layer in pending:
                await conn.execute('INSERT INTO multi_memory(character_id,content,layer) VALUES($1,$2,$3)',cid,content,layer)
    return dict(preview=preview,add=len(pending),skip=len(rows)-len(pending))
