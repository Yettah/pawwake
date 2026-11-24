"""HTTP smoke test for a disposable running gateway. No model calls or real memories."""
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = os.environ.get('PAWWAKE_SMOKE_URL', 'http://127.0.0.1:8000').rstrip('/')

def request(path, key=None):
    headers = {'Authorization': 'Bearer ' + key} if key else {}
    try:
        with urlopen(Request(BASE + path, headers=headers), timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, None

def check():
    for _ in range(60):
        try:
            status, body = request('/')
            if status == 200 and body.get('status') == 'running':
                break
        except (URLError, TimeoutError):
            pass
        time.sleep(1)
    else:
        raise RuntimeError('Gateway did not become ready')
    if not body.get('database_enabled') or not body.get('memory_enabled'):
        raise RuntimeError('Persistence or memory is disabled')
    for path, key in [('/v1/models', None), ('/v1/models', 'pwchar_' + 'x'*43), ('/character-mcp', 'pwchar_' + 'x'*43)]:
        status, _ = request(path, key)
        if status not in (401, 403):
            raise RuntimeError(f'Expected authentication rejection for {path}; got {status}')
    print('HTTP startup and negative authentication smoke checks passed')

if __name__ == '__main__':
    check()
