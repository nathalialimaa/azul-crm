"""Estado durável: SQLite local; Redis REST na Vercel. Nunca usa memória como persistência."""

import json
import os
import sqlite3
import time
from pathlib import Path

import httpx


class StorageUnavailable(RuntimeError):
    pass


class Storage:
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.hosted = bool(os.getenv("VERCEL"))
        self.path = Path(
            os.getenv(
                "CRM_WEB_STATE", str(Path(__file__).resolve().parents[2] / ".runtime/web.sqlite3")
            )
        )

    def redis(self, *command):
        if not self.url.startswith("https://") or not self.token:
            raise StorageUnavailable(
                "Configure Redis REST para persistência e controle de cota na Vercel."
            )
        try:
            r = httpx.post(
                self.url,
                headers={"Authorization": "Bearer " + self.token},
                json=list(command),
                timeout=10,
            )
            r.raise_for_status()
            body = r.json()
            if body.get("error"):
                raise ValueError()
            return body["result"]
        except (httpx.HTTPError, ValueError, KeyError):
            raise StorageUnavailable(
                "Persistência indisponível; nenhuma geração foi iniciada."
            ) from None

    @property
    def remote(self):
        return self.hosted or bool(self.url)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=15)
        db.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        return db

    def get(self, key):
        if self.remote:
            raw = self.redis("GET", "azul:" + key)
        else:
            with self.connect() as db:
                row = db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
                raw = row[0] if row else None
        return json.loads(raw) if raw else None

    def put(self, key, value, ttl=86400):
        raw = json.dumps(value, ensure_ascii=False, default=str)
        if self.remote:
            self.redis("SET", "azul:" + key, raw, "EX", ttl)
        else:
            with self.connect() as db:
                db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, raw))

    def reserve(self, bucket, limit, cooldown=20):
        now = time.time()
        if self.remote:
            script = "local n=tonumber(redis.call('GET',KEYS[1]) or '0'); local t=tonumber(redis.call('GET',KEYS[2]) or '0'); if n>=tonumber(ARGV[1]) then return -1 end; if tonumber(ARGV[3])>0 and tonumber(ARGV[2])-t<tonumber(ARGV[3]) then return -2 end; redis.call('SET',KEYS[1],n+1,'EX',172800); redis.call('SET',KEYS[2],ARGV[2],'EX',172800); return n+1"
            return int(
                self.redis(
                    "EVAL",
                    script,
                    2,
                    "azul:quota:" + bucket,
                    "azul:last:" + bucket,
                    limit,
                    now,
                    cooldown,
                )
            )
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            key = "quota:" + bucket
            row = db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
            value = json.loads(row[0]) if row else {"count": 0, "last": 0}
            if value["count"] >= limit:
                return -1
            if cooldown > 0 and now - value["last"] < cooldown:
                return -2
            value = {"count": value["count"] + 1, "last": now}
            db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, json.dumps(value)))
            return value["count"]

    def history(self):
        if self.remote:
            return [json.loads(v) for v in self.redis("LRANGE", "azul:decisions", 0, 199)]
        return self.get("history") or []

    def decide(self, draft_id, row):
        raw = json.dumps(row, ensure_ascii=False, default=str)
        if self.remote:
            script = "if redis.call('EXISTS',KEYS[1])==1 then return 0 end; redis.call('SET',KEYS[1],ARGV[1]); redis.call('LPUSH',KEYS[2],ARGV[1]); return 1"
            return bool(
                self.redis("EVAL", script, 2, "azul:review:" + draft_id, "azul:decisions", raw)
            )
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            key = "review:" + draft_id
            if db.execute("SELECT 1 FROM kv WHERE key=?", (key,)).fetchone():
                return False
            old = db.execute("SELECT value FROM kv WHERE key='history'").fetchone()
            history = [row] + (json.loads(old[0]) if old else [])
            db.execute("INSERT INTO kv VALUES (?,?)", (key, raw))
            db.execute(
                "INSERT OR REPLACE INTO kv VALUES ('history',?)",
                (json.dumps(history, ensure_ascii=False, default=str),),
            )
            return True
