"""Validated per-character overrides; empty fields inherit global settings."""
import json

FIELDS = {'chat_model', 'memory_model', 'embedding_model', 'prompt_mode', 'temperature', 'max_tokens', 'memory_enabled', 'extraction_enabled', 'history_enabled', 'history_chars'}

def validate(data):
    if not isinstance(data, dict) or set(data)-FIELDS:
        raise ValueError('Unknown settings')
    out = {}
    for k,v in data.items():
        if v is None or v == '': continue
        if k.endswith('_enabled'):
            if type(v) is not bool: raise ValueError(k)
        elif k == 'temperature':
            if type(v) not in (int,float) or not 0 <= v <= 2: raise ValueError(k)
        elif k == 'history_chars':
            if type(v) is not int or not 0 <= v <= 24000: raise ValueError(k)
        elif k == 'max_tokens':
            if type(v) is not int or not 1 <= v <= 131072: raise ValueError(k)
        elif k == 'prompt_mode':
            if v not in ('central','merge'): raise ValueError(k)
        elif not isinstance(v,str) or not v.strip() or len(v)>200:
            raise ValueError(k)
        out[k]=v
    return out

async def load(conn,cid):
    raw=await conn.fetchval('SELECT settings FROM multi_characters WHERE id=$1',cid)
    if raw is None: raise PermissionError('character unavailable')
    return validate(json.loads(raw) if isinstance(raw,str) else raw)
