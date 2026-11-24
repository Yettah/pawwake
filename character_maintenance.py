"""Conservative, explicit maintenance of exact duplicate non-core memories."""
from character_storage import CharacterStorage

class CharacterMaintenance:
    def __init__(self, storage):
        if not isinstance(storage, CharacterStorage):
            raise TypeError('character storage required')
        self.storage = storage

    async def preview(self):
        groups = {}
        for row in await self.storage.memories():
            groups.setdefault(row['content'], []).append(row)
        actions = []
        for rows in groups.values():
            if len(rows) < 2 or any(r['layer'] == 1 for r in rows):
                continue
            rows.sort(key=lambda r: (r['layer'], r['id']))
            for row in rows[1:]:
                actions.append((rows[0]['id'], row['id']))
        return actions

    async def apply(self, keep_id, duplicate_id):
        if type(keep_id) is not int or type(duplicate_id) is not int or keep_id == duplicate_id:
            raise ValueError('distinct memory IDs required')
        return await self.storage.archive_duplicate(keep_id, duplicate_id)

    async def restore(self, archive_id):
        return await self.storage.restore_archived_memory(archive_id)
