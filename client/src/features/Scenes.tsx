import { FormEvent, useEffect, useState } from 'react';
type Player = { entity_id: string; name: string; volume: number };
type Target = { entity_id: string; volume: number; state: string };
type Scene = { id: string; name: string; version: number; targets: Target[] };
type Job = { id: string; status: string; created_at: string; result: unknown };
async function call<T>(path: string, body?: unknown, key?: string): Promise<T> {
  const r = await fetch('/api' + path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', ...(key ? { 'Idempotency-Key': key } : {}) }, body: JSON.stringify(body) });
  const data = await r.json(); if (!r.ok) throw new Error(data.error); return data;
}
export function Scenes({ players }: { players: Player[] }) {
  const [scenes, setScenes] = useState<Scene[]>([]), [jobs, setJobs] = useState<Job[]>([]);
  const [targets, setTargets] = useState<Target[]>([]), [name, setName] = useState('');
  const [error, setError] = useState(''), [busy, setBusy] = useState(false);
  async function load() { const [s, j] = await Promise.all([call<Scene[]>('/scenes'), call<Job[]>('/jobs')]); setScenes(s); setJobs(j); }
  useEffect(() => { const refresh = () => load().catch(e => setError(String(e))); refresh(); const timer = window.setInterval(refresh, 3000); return () => clearInterval(timer); }, []);
  async function action(work: () => Promise<unknown>) { setBusy(true); setError(''); try { await work(); await load(); } catch (e) { setError(String(e)); } finally { setBusy(false); } }
  function save(e: FormEvent) { e.preventDefault(); void action(async () => { await call('/scenes', { name, targets }); setName(''); setTargets([]); }); }
  return <section className="scenes"><h2>Scenes and command history</h2>{error && <p role="alert">{error}</p>}
    <form onSubmit={save}><input value={name} onChange={e => setName(e.target.value)} placeholder="Scene name" required />
      {players.map(player => { const target = targets.find(t => t.entity_id === player.entity_id); return <div className="scene-target" key={player.entity_id}>
        <label><input type="checkbox" checked={!!target} onChange={e => setTargets(rows => e.target.checked ? [...rows, { entity_id: player.entity_id, volume: Math.min(player.volume, 80), state: 'unchanged' }] : rows.filter(t => t.entity_id !== player.entity_id))} />{player.name}</label>
        {target && <><input aria-label={`${player.name} scene volume`} type="number" min="0" max="80" value={target.volume} onChange={e => setTargets(rows => rows.map(t => t.entity_id === player.entity_id ? { ...t, volume: Number(e.target.value) } : t))} />
          <select aria-label={`${player.name} scene playback`} value={target.state} onChange={e => setTargets(rows => rows.map(t => t.entity_id === player.entity_id ? { ...t, state: e.target.value } : t))}><option value="unchanged">Keep playback</option><option value="playing">Play</option><option value="paused">Pause</option></select></>}
      </div>; })}<button disabled={busy || !targets.length}>Save scene</button></form>
    <div className="scene-list">{scenes.map(scene => <article key={scene.id}><h3>{scene.name}</h3><p>{scene.targets.length} players · version {scene.version}</p><button disabled={busy} onClick={() => action(() => call(`/scenes/${scene.id}/execute`, {}, crypto.randomUUID()))}>Apply scene</button></article>)}</div>
    <h3>Recent jobs</h3>{jobs.slice(0, 10).map(job => <details key={job.id}><summary>{job.created_at} · {job.status}</summary><pre>{JSON.stringify(job.result, null, 2)}</pre></details>)}
  </section>;
}
