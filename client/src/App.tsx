import { Scenes } from './features/Scenes';
import { useEffect, useState } from 'react';

type Player={entity_id:string;name:string;state:string;volume:number;track:string;artist:string;source:string;provider:string};
type Snapshot={provider:string;players:Player[];error?:string};
type Preset={name:string;volume:number};
const presets:Preset[]=[{name:'Quiet',volume:18},{name:'Everyday',volume:35},{name:'Lively',volume:55}];
async function api<T>(url:string,body?:unknown):Promise<T>{const r=await fetch(url,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const data=await r.json();if(!r.ok)throw new Error(data.error||'The player could not be reached.');return data;}

function PlayerCard({player,onAction,busy}:{player:Player;onAction:(id:string,action:string,volume?:number)=>void;busy:boolean}){
  const [volume,setVolume]=useState(player.volume);
  useEffect(()=>setVolume(player.volume),[player.volume]);
  return <article className="player-card"><div className="player-top"><div className="speaker-icon">♫</div><div className="player-name"><h3>{player.name}</h3><span><i className={`status ${player.state==='playing'?'playing':''}`}/>{player.state==='playing'?'Playing':'Paused'} <b>·</b> {player.provider}</span></div><button className="dots" aria-label="Player menu">•••</button></div>
    <div className="track"><div className="cover">{player.state==='playing'?'♫':'◌'}</div><div><strong>{player.track||'Nothing queued'}</strong><small>{player.artist||player.source||'Choose something to play'}</small></div></div>
    <div className="player-controls"><button aria-label="Previous track" onClick={()=>onAction(player.entity_id,'previous')} disabled={busy}>◀|</button><button className="play-button" onClick={()=>onAction(player.entity_id,'toggle')} disabled={busy}>{player.state==='playing'?'Ⅱ':'▶'}</button><button aria-label="Next track" onClick={()=>onAction(player.entity_id,'next')} disabled={busy}>|▶</button><span className="source-label">{player.source||'No source'}</span></div>
    <div className="volume-row"><span>◖</span><input aria-label={`Volume for ${player.name}`} type="range" min="0" max="100" value={volume} onChange={e=>setVolume(Number(e.target.value))} onMouseUp={()=>onAction(player.entity_id,'volume',volume)} onTouchEnd={()=>onAction(player.entity_id,'volume',volume)}/><strong>{volume}%</strong></div>
    <div className="preset-row">{presets.map(p=><button key={p.name} onClick={()=>{setVolume(p.volume);onAction(player.entity_id,'volume',p.volume)}}>{p.name}</button>)}</div>
  </article>;
}

export function App(){
  const [snapshot,setSnapshot]=useState<Snapshot>({provider:'mock',players:[]});const [error,setError]=useState('');const [busy,setBusy]=useState<string|null>(null);const [updated,setUpdated]=useState('');
  async function refresh(){try{const state=await api<Snapshot>('/api/players');setSnapshot(state);setError('');setUpdated(new Date().toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}));}catch(e){setError(e instanceof Error?e.message:'Could not load players.');}}
  useEffect(()=>{refresh();const id=window.setInterval(refresh,12000);return()=>window.clearInterval(id)},[]);
  async function control(id:string,action:string,volume?:number){setBusy(id+action);setError('');try{await api('/api/control',{entity_id:id,action,volume});await refresh();}catch(e){setError(e instanceof Error?e.message:'Control failed.');}finally{setBusy(null)}}
  const playing=snapshot.players.filter(p=>p.state==='playing').length;
  return <div className="layout"><aside className="rail"><div className="logo">A</div><button className="rail-active" title="Rooms">▦</button><button title="Queue">☷</button><button title="Favorites">♡</button><div className="rail-bottom">?</div></aside><main><header className="header"><div className="wordmark">AUDIO<span>CONSOLE</span></div><div className="header-right"><span className="connection"><i/> {snapshot.provider==='home-assistant'?'Home Assistant':'Local demo'}</span><button className="refresh" onClick={refresh}>↻ <span>Refresh</span></button><div className="profile">H</div></div></header>
    <div className="page"><section className="title-row"><div><div className="overline">YOUR SPACE <span> / </span> AUDIO</div><h1>Room controls</h1><p>Quick controls for the speakers around your place.</p></div><button className="manage">⚙ <span>Manage players</span></button></section>
    <section className="summary"><div className="summary-item"><span className="summary-icon mint">♫</span><div><small>ROOMS</small><strong>{snapshot.players.length} <em>connected</em></strong></div></div><div className="summary-item"><span className="summary-icon gold">◉</span><div><small>PLAYING NOW</small><strong>{playing} <em>active</em></strong></div></div><div className="summary-item"><span className="summary-icon blue">⌚</span><div><small>LAST UPDATED</small><strong>{updated||'—'} <em>local time</em></strong></div></div><div className="summary-end"><span className="pulse"/>System online</div></section>
    {error&&<div className="error">{error}<button onClick={refresh}>Retry</button></div>}
    <section className="rooms-heading"><div><h2>Available rooms <span>{snapshot.players.length}</span></h2><p>Playback, source, and volume controls per speaker.</p></div><button className="view">⌘ <span>Room view</span></button></section>
    {snapshot.players.length?<div className="grid">{snapshot.players.map(player=><PlayerCard key={player.entity_id} player={player} onAction={control} busy={busy===player.entity_id+'toggle'||busy===player.entity_id+'volume'}/>)}</div>:<div className="empty">No media players are configured yet.</div>}
    <Scenes players={snapshot.players}/><section className="note"><span>ⓘ</span><p><strong>Local control surface</strong><br/>Audio Console sends controls to the configured Home Assistant player. In demo mode, controls update an in-memory mock player.</p><a href="/api/health">API status →</a></section><footer>Audio Console <span>INTERNAL USE</span><span className="footer-right">Updated {updated||'—'}</span></footer></div></main></div>;
}
