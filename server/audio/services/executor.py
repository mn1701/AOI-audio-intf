"""Bounded, ordered scene execution with partial-failure reporting."""
import math
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

class QueueFull(RuntimeError):
    pass

class SceneExecutor:
    def __init__(self, provider, store):
        self.provider, self.store = provider, store
        # Scene jobs execute in submission order. Physical players are not transactional.
        self.pool = ThreadPoolExecutor(max_workers=1,thread_name_prefix='audio-scene')
        self.capacity = threading.BoundedSemaphore(32)
        self.submit_lock = threading.Lock()
        self.device_lock = threading.RLock()

    def validate(self, targets):
        if not isinstance(targets,list) or not 1 <= len(targets) <= 24: raise ValueError('Choose 1 to 24 players.')
        known = {p['entity_id'] for p in self.provider.players()['players']}
        seen=set()
        for target in targets:
            if not isinstance(target,dict): raise ValueError('Invalid target.')
            entity=target.get('entity_id')
            if not isinstance(entity,str) or entity not in known or entity in seen: raise ValueError('Unknown or duplicated player.')
            seen.add(entity)
            volume=target.get('volume')
            if isinstance(volume,bool) or not isinstance(volume,(int,float)) or not math.isfinite(volume) or not 0<=volume<=80:
                raise ValueError('Scene volume must be between 0 and 80.')
            if target.get('state','unchanged') not in {'playing','paused','unchanged'}: raise ValueError('Invalid playback state.')
        return [{k:t[k] for k in ('entity_id','volume','state') if k in t} for t in targets]

    def submit(self, targets, key):
        targets=self.validate(targets)
        if not isinstance(key,str) or not 8 <= len(key) <= 120: raise ValueError('Provide an Idempotency-Key of 8 to 120 characters.')
        with self.submit_lock:
            if not self.capacity.acquire(blocking=False): raise QueueFull('Command queue is full.')
            owned = True
            try:
                job_id,created=self.store.insert_job(str(uuid.uuid4()),key,targets)
                result=self.store.jobs(job_id)[0]
                if created:
                    self.pool.submit(self._run,job_id,targets)
                    owned = False # Worker owns the capacity permit from here.
                return result
            finally:
                if owned: self.capacity.release()

    def _run(self, job_id, targets):
        results=[]
        try:
            self.store.update_job(job_id,'running')
            with self.device_lock:
                before={p['entity_id']:p for p in self.provider.players()['players']}
                for target in targets:
                    entity=target['entity_id']
                    steps=[]
                    try:
                        self.provider.control(entity,'volume',target['volume'])
                        steps.append('volume')
                        state=target.get('state','unchanged')
                        if state!='unchanged':
                            self.provider.control(entity,'play' if state=='playing' else 'pause')
                            steps.append(state)
                        results.append({'entity_id':entity,'ok':True,'steps':steps,'before':before.get(entity)})
                    except Exception as exc:
                        # No retry: next/previous or toggle commands must never be accidentally duplicated.
                        results.append({'entity_id':entity,'ok':False,'steps':steps,'error':str(exc),'before':before.get(entity)})
            status='succeeded' if all(r['ok'] for r in results) else 'partial' if any(r['ok'] for r in results) else 'failed'
            self.store.update_job(job_id,status,results)
        except Exception as exc:
            self.store.update_job(job_id,'failed',{'error':str(exc),'players':results})
        finally:
            self.capacity.release()
