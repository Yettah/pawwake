"""Optional character-scoped semantic recall; bounded lazy vector cache."""
import math
import json
import logging

log = logging.getLogger(__name__)

def normalize(values, dim):
    if not isinstance(values, list) or len(values) != dim or any(type(x) not in (int,float) or not math.isfinite(x) for x in values):
        raise ValueError('invalid embedding')
    norm = math.hypot(*values)
    if not norm or not math.isfinite(norm):
        raise ValueError('invalid embedding norm')
    return [x/norm for x in values]

class SemanticRecall:
    def __init__(self, client, url, key, model, dim):
        if not 1 <= dim <= 4096 or not key or not model:
            raise ValueError('invalid embedding configuration')
        self.client, self.url, self.key, self.model, self.dim = client, url.rstrip('/')+'/embeddings', key, model, dim
        self.profile = json.dumps([self.url,model,dim])

    async def embed(self, texts):
        response = await self.client.post(self.url, headers={'Authorization':'Bearer '+self.key}, json={'model':self.model,'input':texts,'dimensions':self.dim})
        response.raise_for_status()
        data = sorted(response.json()['data'], key=lambda x:x['index'])
        if [x['index'] for x in data] != list(range(len(texts))):
            raise ValueError('invalid embedding response')
        return [normalize(x['embedding'],self.dim) for x in data]

    async def scores(self, storage, query):
        rows = await storage.vector_candidates(self.profile)
        if not rows:
            return {}
        q, = await self.embed([query[:4000]])
        missing = [r for r in rows if r['embedding'] is None][:32]
        fresh = {}
        if missing:
            vectors = await self.embed([r['content'][:4000] for r in missing])
            for r,v in zip(missing,vectors):
                await storage.save_vector(r['id'],self.profile,v)
                fresh[r['id']] = v
        result = {}
        for r in rows:
            v = fresh.get(r['id'])
            if v is None and r['embedding'] is not None:
                v = normalize(json.loads(r['embedding']) if isinstance(r['embedding'],str) else r['embedding'],self.dim)
            if v is not None:
                result[r['id']] = sum(a*b for a,b in zip(q,v))
        return result
