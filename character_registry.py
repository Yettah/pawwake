"""Experimental character registry; deliberately not wired to live gateway routes.
Keys are high-entropy bearer credentials; only SHA-256 digests are persisted.
"""
import hashlib
import secrets
import uuid

DDL = '''CREATE TABLE IF NOT EXISTS multi_characters (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
    system_prompt TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS multi_character_keys (
    key_digest TEXT PRIMARY KEY,
    character_id UUID NOT NULL REFERENCES multi_characters(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);'''


def digest_key(key):
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def new_key():
    return 'pwchar_' + secrets.token_urlsafe(32)


async def initialize(conn):
    await conn.execute(DDL)
    await conn.execute("ALTER TABLE multi_characters ADD COLUMN IF NOT EXISTS settings JSONB NOT NULL DEFAULT '{}'::jsonb")


async def create_character(conn, name, system_prompt=''):
    name = name.strip()
    if not 1 <= len(name) <= 120:
        raise ValueError('人物名称必须为1至120字符')
    character_id = uuid.uuid4()
    key = new_key()
    async with conn.transaction():
        await conn.execute('INSERT INTO multi_characters(id,name,system_prompt) VALUES($1,$2,$3)', character_id, name, system_prompt)
        await conn.execute('INSERT INTO multi_character_keys(key_digest,character_id) VALUES($1,$2)', digest_key(key), character_id)
    return character_id, key


async def resolve_character(conn, key):
    if not isinstance(key, str) or not key.startswith('pwchar_') or len(key) != 50:
        return None
    return await conn.fetchval('SELECT character_id FROM multi_character_keys WHERE key_digest=$1 AND revoked_at IS NULL', digest_key(key))


async def revoke_key(conn, key):
    await conn.execute('UPDATE multi_character_keys SET revoked_at=now() WHERE key_digest=$1 AND revoked_at IS NULL', digest_key(key))
