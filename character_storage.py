"""Experimental isolated storage, not connected to production gateway.
All operations require a registry-resolved UUID. No fallback to legacy tables.
"""
from uuid import UUID
import json
from character_registry import resolve_character

DDL = '''
CREATE TABLE IF NOT EXISTS multi_memory (
 character_id UUID NOT NULL REFERENCES multi_characters(id) ON DELETE CASCADE,
 id BIGINT GENERATED ALWAYS AS IDENTITY,
 content TEXT NOT NULL, layer INTEGER NOT NULL CHECK(layer BETWEEN 1 AND 3),
 PRIMARY KEY(character_id,id)
);
CREATE TABLE IF NOT EXISTS multi_memory_archive (
 character_id UUID NOT NULL REFERENCES multi_characters(id) ON DELETE CASCADE,
 id BIGINT GENERATED ALWAYS AS IDENTITY,
 original_id BIGINT NOT NULL, content TEXT NOT NULL, layer INTEGER NOT NULL,
 archived_at TIMESTAMPTZ NOT NULL DEFAULT now(), restored_at TIMESTAMPTZ,
 PRIMARY KEY(character_id,id)
);
CREATE TABLE IF NOT EXISTS multi_vectors (
 character_id UUID NOT NULL, memory_id BIGINT NOT NULL, profile TEXT NOT NULL,
 embedding JSONB NOT NULL, PRIMARY KEY(character_id,memory_id,profile),
 FOREIGN KEY(character_id,memory_id) REFERENCES multi_memory(character_id,id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS multi_conversation (
 character_id UUID NOT NULL REFERENCES multi_characters(id) ON DELETE CASCADE,
 id BIGINT GENERATED ALWAYS AS IDENTITY,
 session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT,
 PRIMARY KEY(character_id,id)
);
CREATE INDEX IF NOT EXISTS multi_conversation_session ON multi_conversation(character_id,session_id,id);
CREATE TABLE IF NOT EXISTS multi_cache (
 character_id UUID NOT NULL REFERENCES multi_characters(id) ON DELETE CASCADE,
 session_id TEXT NOT NULL, state JSONB NOT NULL,
 PRIMARY KEY(character_id,session_id)
);
'''

async def initialize(conn):
    await conn.execute(DDL)

class CharacterStorage:
    def __init__(self, conn, character_id):
        if not isinstance(character_id, UUID):
            raise ValueError('valid character UUID required')
        self._conn = conn
        self._id = character_id

    @classmethod
    async def from_key(cls, conn, key):
        cid = await resolve_character(conn, key)
        if cid is None:
            raise PermissionError('invalid character credential')
        return cls(conn, cid)

    async def add_memory(self, content, layer):
        if layer not in (1,2,3):
            raise ValueError('invalid layer')
        return await self._conn.fetchval('INSERT INTO multi_memory(character_id,content,layer) VALUES($1,$2,$3) RETURNING id', self._id, content, layer)

    async def memories(self):
        return await self._conn.fetch('SELECT id,content,layer FROM multi_memory WHERE character_id=$1 ORDER BY id', self._id)

    async def delete_memory(self, memory_id):
        return await self._conn.execute('DELETE FROM multi_memory WHERE character_id=$1 AND id=$2', self._id, memory_id)

    async def append_message(self, session_id, role, content):
        return await self._conn.fetchval('INSERT INTO multi_conversation(character_id,session_id,role,content) VALUES($1,$2,$3,$4) RETURNING id', self._id, session_id, role, content)

    async def messages(self, session_id):
        return await self._conn.fetch('SELECT id,role,content FROM multi_conversation WHERE character_id=$1 AND session_id=$2 ORDER BY id', self._id, session_id)

    async def recent_messages(self, session_id, limit=40):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('invalid history limit')
        rows = await self._conn.fetch('SELECT id,role,content FROM multi_conversation WHERE character_id=$1 AND session_id=$2 ORDER BY id DESC LIMIT $3', self._id, session_id, limit)
        return list(reversed(rows))

    async def save_cache(self, session_id, state):
        await self._conn.execute('INSERT INTO multi_cache(character_id,session_id,state) VALUES($1,$2,$3::jsonb) ON CONFLICT(character_id,session_id) DO UPDATE SET state=EXCLUDED.state', self._id, session_id, json.dumps(state))

    async def load_cache(self, session_id):
        return await self._conn.fetchval('SELECT state FROM multi_cache WHERE character_id=$1 AND session_id=$2', self._id, session_id)

    async def vector_candidates(self, profile):
        return await self._conn.fetch("""SELECT m.id,m.content,v.embedding FROM multi_memory m
            LEFT JOIN multi_vectors v ON v.character_id=m.character_id AND v.memory_id=m.id AND v.profile=$2
            WHERE m.character_id=$1 ORDER BY (v.embedding IS NULL) DESC,m.id DESC LIMIT 500""", self._id, profile)

    async def save_vector(self, memory_id, profile, vector):
        await self._conn.execute("""INSERT INTO multi_vectors(character_id,memory_id,profile,embedding)
            VALUES($1,$2,$3,$4::jsonb) ON CONFLICT(character_id,memory_id,profile)
            DO UPDATE SET embedding=EXCLUDED.embedding""", self._id,memory_id,profile,json.dumps(vector))

    async def archive_duplicate(self, keep_id, duplicate_id):
        if keep_id == duplicate_id:
            raise ValueError('distinct IDs required')
        async with self._conn.transaction():
            rows = await self._conn.fetch("""SELECT id,content,layer FROM multi_memory
                WHERE character_id=$1 AND id IN ($2,$3) ORDER BY id FOR UPDATE""", self._id, keep_id, duplicate_id)
            by_id = {r['id']: r for r in rows}
            if keep_id not in by_id or duplicate_id not in by_id:
                return None
            keep, dup = by_id[keep_id], by_id[duplicate_id]
            if keep['layer'] == 1 or dup['layer'] == 1 or keep['layer'] > dup['layer'] or keep['content'] != dup['content']:
                return None
            archive_id = await self._conn.fetchval("""INSERT INTO multi_memory_archive
                (character_id,original_id,content,layer) VALUES($1,$2,$3,$4) RETURNING id""", self._id, duplicate_id, dup['content'], dup['layer'])
            await self.delete_memory(duplicate_id)
            return archive_id

    async def restore_archived_memory(self, archive_id):
        async with self._conn.transaction():
            row = await self._conn.fetchrow("""SELECT content,layer FROM multi_memory_archive
                WHERE character_id=$1 AND id=$2 AND restored_at IS NULL FOR UPDATE""", self._id, archive_id)
            if row is None:
                return None
            new_id = await self.add_memory(row['content'], row['layer'])
            await self._conn.execute("""UPDATE multi_memory_archive SET restored_at=now()
                WHERE character_id=$1 AND id=$2""", self._id, archive_id)
            return new_id
