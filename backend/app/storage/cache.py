import hashlib, json, sqlite3, time
from pathlib import Path

class SQLiteCache:
    def __init__(self, path="data/cache.sqlite3", ttl_seconds=900):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        with sqlite3.connect(self.path) as con:
            con.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL NOT NULL)")
            con.commit()

    def _key(self, provider, endpoint, params):
        raw = json.dumps([provider, endpoint, params], sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, provider, endpoint, params):
        key = self._key(provider, endpoint, params)
        with sqlite3.connect(self.path) as con:
            row = con.execute("SELECT value, expires FROM cache WHERE key=?", (key,)).fetchone()
        if not row or row[1] < time.time():
            return None
        return json.loads(row[0])

    def set(self, provider, endpoint, params, value, ttl=None):
        key = self._key(provider, endpoint, params)
        with sqlite3.connect(self.path) as con:
            con.execute("INSERT OR REPLACE INTO cache(key,value,expires) VALUES(?,?,?)", (key, json.dumps(value, default=str), time.time() + (ttl or self.ttl_seconds)))
            con.commit()
