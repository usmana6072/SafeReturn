"use client";
import Link from 'next/link';
import {useEffect,useRef,useState} from 'react';
import {AdminCard,AdminEmptyState,AdminPageContainer,AdminPageHeader,AdminStatusBadge} from './admin-ui';
import {AdminConfirmDialog} from './admin-confirm-dialog';
import {useAdminRole} from './admin-shell';
import {canReadSync,syncPage,syncStates,syncRetryReceipt,type SyncRecord} from '../lib/finance-storage-contract';
import {useFinanceStorageRead} from '../lib/use-finance-storage-read';
import styles from './admin-finance-sync.module.css';
const root='/admin/finance/sheet-sync';
const statusLabel={pending:'Pending',retry:'Retry queued',synced:'Synced (recorded)',failed:'Failed'};
function Badge({value}:{value:SyncRecord['status']}){return <AdminStatusBadge label={statusLabel[value]} variant={value==='failed'?'danger':value==='synced'?'info':'warning'}/>;}
export function AdminFinanceSync({syncId,ur=false,admitted=false,retryAdmitted=false}:{syncId?:string;ur?:boolean;admitted?:boolean;retryAdmitted?:boolean}){
  const role=useAdminRole();return <div className={styles.screen} dir={ur?'rtl':'ltr'}><AdminPageContainer>
    <AdminPageHeader title={syncId?'Finance Sync Details':'Finance Sheet Sync'} description="Review stored reporting synchronization metadata." actions={syncId&&<Link href={root} prefetch={false}>Back to Finance Sheet Sync</Link>}/>
    {!canReadSync(role.authenticatedRoles)?<AdminEmptyState title="Access denied" description="Finance, Security Admin or Superadmin with verified MFA is required."/>:!admitted?<AdminCard><section className={styles.body}><h2>Live Finance integration disabled</h2><p>No synchronization records are loaded. Retry is unavailable pending acceptance.</p></section></AdminCard>:<SyncRecords key={syncId??'list'} syncId={syncId} retryAdmitted={retryAdmitted}/>}
  </AdminPageContainer></div>;
}
function SyncRecords({syncId,retryAdmitted}:{syncId?:string;retryAdmitted:boolean}){
  const read=useFinanceStorageRead(false,syncPage,syncId);
  const [status,setStatus]=useState('all'),[reference,setReference]=useState(''),[cursors,setCursors]=useState<(string|null)[]>([null]),[index,setIndex]=useState(0);
  const [selected,setSelected]=useState<SyncRecord|null>(null),[sending,setSending]=useState(false),[uncertain,setUncertain]=useState(false),[notice,setNotice]=useState('');
  const inFlight=useRef(false);
  useEffect(()=>{setCursors([new URLSearchParams(location.search).get('cursor')]);},[]);
  const items=(read.data?.items??[]).filter(r=>(!syncId||r.id===syncId.toLowerCase())&&(status==='all'||r.status===status)&&(!reference.trim()||r.order_id.includes(reference.trim().toLowerCase())||r.id.includes(reference.trim().toLowerCase())));
  function previous(){const q=new URLSearchParams(read.query.current);q.delete('cursor');if(cursors[index-1])q.set('cursor',cursors[index-1]!);setIndex(index-1);void read.load(q);}
  async function retry(){
    if(!selected||inFlight.current||uncertain||!retryAdmitted)return;inFlight.current=true;setSending(true);setNotice('');
    const id=selected.id;
    try{const response=await fetch(root+'/api',{method:'POST',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(15000),headers:{'Content-Type':'application/json'},body:JSON.stringify({id,confirmed:true})});
      if(!response.ok){if([400,404,409,422,429].includes(response.status)){setNotice('Retry refused. Review the refreshed synchronization state before another confirmation.');await read.load(read.query.current);return;}if([401,403].includes(response.status))read.clear();throw Error();}
      if(response.status!==202)throw Error();syncRetryReceipt(await response.json(),id);
      setNotice('Retry queued. This does not confirm successful spreadsheet synchronization.');await read.load(read.query.current);
    }catch{setUncertain(true);setNotice('Retry outcome unknown. Do not submit again. Refresh metadata and obtain an authorized review before any further retry.');}
    finally{setSelected(null);setSending(false);inFlight.current=false;}
  }
  return <>
    <p className={styles.notice}>PostgreSQL remains authoritative. A queued retry is not a completed spreadsheet update; a synchronization failure does not invalidate a payment.</p>
    {!syncId&&<AdminCard><div className={styles.toolbar}><label>Status (this page)<select aria-label="Status (this page)" value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All statuses</option>{syncStates.map(s=><option key={s} value={s}>{statusLabel[s]}</option>)}</select></label><label>Reference (this page)<input maxLength={36} value={reference} onChange={e=>setReference(e.target.value)} autoComplete="off"/></label><button onClick={()=>{setStatus('all');setReference('');}}>Clear filters</button></div></AdminCard>}
    <div className={styles.toolbar}><button disabled={read.busy||sending} onClick={()=>void read.load(read.query.current)}>Refresh sync records</button><p>Filters apply to this loaded page. No reconciliation total is provided.</p></div>
    {read.busy&&<p role="status">Loading sync metadata…</p>}{read.error&&<p role="alert">{read.error}</p>}{notice&&<p role={uncertain?'alert':'status'}>{notice}</p>}
    {read.data&&!items.length&&<AdminEmptyState title={syncId?'Sync record not on this authorized page':'No sync records on this page'} description="This bounded page does not establish absence from the entire history."/>}
    {!syncId&&read.data&&!!items.length&&<AdminCard><div className={styles.scroll} role="region" aria-label="Finance synchronization metadata" tabIndex={0}><table><thead><tr>{['Sync ID','Order reference','Status','Attempts','Export version','Updated','Last synced','Details'].map(l=><th key={l} scope="col">{l}</th>)}</tr></thead><tbody>{items.map(r=><tr key={r.id}><td className={styles.mono}>{r.id}</td><td className={styles.mono}>{r.order_id}</td><td><Badge value={r.status}/></td><td>{r.attempt_count}</td><td>{r.last_export_version}</td><td>{r.updated_at}</td><td>{r.last_synced_at??'—'}</td><td><Link prefetch={false} href={root+'/'+r.id+(read.query.current.size?'?'+read.query.current:'')}>View details</Link></td></tr>)}</tbody></table></div><p className={styles.count}>{items.length} shown on this page.</p></AdminCard>}
    {syncId&&items.map(r=><AdminCard key={r.id}><section className={styles.body}><h2>Synchronization metadata</h2><dl className={styles.facts}><div><dt>Status</dt><dd><Badge value={r.status}/></dd></div>{[['Sync ID',r.id],['Order reference',r.order_id],['Attempts',r.attempt_count],['Export version',r.last_export_version],['Updated',r.updated_at],['Last synced',r.last_synced_at],['Safe failure code',r.last_error_code]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value??'—'}</dd></div>)}</dl><p>Created time, spreadsheet contents and recipient financial details are not provided here.</p>
      <button disabled={!retryAdmitted||uncertain||sending||!['failed','retry'].includes(r.status)} onClick={()=>setSelected(r)}>Review sync retry</button><p>{uncertain?'Retry locked pending review of the unknown result.':!retryAdmitted?'Retry disabled pending live mutation acceptance.':'Retry requires an explicit confirmation and current backend eligibility.'}</p>
    </section></AdminCard>)}
    {read.data&&<div className={styles.toolbar}><button disabled={read.busy||index===0||sending} onClick={previous}>Previous page</button><span>Page {index+1}{cursors[0]?' from linked cursor':''}</span><button disabled={read.busy||!read.data.next_cursor||sending} onClick={()=>{const next=read.data!.next_cursor!;setCursors([...cursors.slice(0,index+1),next]);setIndex(index+1);const q=new URLSearchParams(read.query.current);q.set('cursor',next);void read.load(q);}}>Next page</button></div>}
    <AdminConfirmDialog isOpen={!!selected} title="Confirm Finance Sync Retry" message={'Queue one retry for '+(selected?.id??'')+'? This may update the approved external spreadsheet. Queuing does not confirm completion.'} confirmLabel="Queue sync retry" loading={sending} onConfirm={()=>void retry()} onCancel={()=>{if(!sending)setSelected(null);}}/>
  </>;
}
