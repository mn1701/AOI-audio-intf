"""Durable scene definitions and command execution records."""
import json
import os
import sqlite3
from contextlib import contextmanager, closing
from pathlib import Path

class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('AUDIO_DATABASE', Path(__file__).resolve().parents[1] / 'data/audio.sqlite3'))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS scenes(id TEXT PRIMARY KEY,name TEXT NOT NULL,version INTEGER NOT NULL,targets TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,idempotency_key TEXT UNIQUE,payload TEXT NOT NULL,
                status TEXT NOT NULL,result TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
              CREATE INDEX IF NOT EXISTS job_creation ON jobs(created_at);
            ''')
            # Never automatically replay a possibly delivered device command after a crash.
            db.execute("UPDATE jobs SET status='interrupted',updated_at=CURRENT_TIMESTAMP WHERE status IN ('queued','running')")

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA busy_timeout=10000')
            with db:
                yield db

    def scenes(self):
        with self.connection() as db:
            return [{**dict(r),'targets':json.loads(r['targets'])} for r in db.execute('SELECT * FROM scenes ORDER BY name')]

    def save_scene(self, scene_id, name, targets, expected):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT version FROM scenes WHERE id=?',(scene_id,)).fetchone()
            current = row['version'] if row else 0
            if current != expected: raise ValueError('Scene version changed. Reload before saving.')
            db.execute('INSERT INTO scenes VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,version=excluded.version,targets=excluded.targets',
                       (scene_id,name,current+1,json.dumps(targets)))
        return {'id':scene_id,'name':name,'version':current+1,'targets':targets}

    def insert_job(self, job_id, key, payload):
        serialized=json.dumps(payload,sort_keys=True,separators=(',',':'))
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM jobs WHERE idempotency_key=?',(key,)).fetchone()
            if row:
                if row['payload']!=serialized: raise ValueError('Idempotency key was used for different commands.')
                return row['id'],False
            db.execute("INSERT INTO jobs(id,idempotency_key,payload,status) VALUES(?,?,?,'queued')",(job_id,key,serialized))
            return job_id,True

    def update_job(self, job_id, status, result=None):
        with self.connection() as db:
            db.execute('UPDATE jobs SET status=?,result=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,json.dumps(result),job_id))

    def jobs(self, job_id=None):
        with self.connection() as db:
            rows=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)) if job_id else db.execute('SELECT * FROM jobs ORDER BY created_at DESC,rowid DESC LIMIT 100')
            return [{**dict(r),'payload':json.loads(r['payload']),'result':json.loads(r['result']) if r['result'] else None} for r in rows]
