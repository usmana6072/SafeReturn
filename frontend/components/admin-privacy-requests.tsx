"use client";

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { useAdminRole } from './admin-shell';
import { canReviewPrivacy, exportId, exportPage, exportQuery, exportStates, type ExportPage, type ExportMetadata } from '../lib/admin-privacy-metadata';
import styles from './admin-privacy-requests.module.css';

const root='/admin/privacy/exports';
function RequestStatus({value}:{value:ExportMetadata['status']}){
  return <AdminStatusBadge label={value} variant={['requested','reviewing','held','retry'].includes(value)?'warning':value==='rejected'?'danger':value==='ready'?'info':'neutral'}/>;
}
export function AdminPrivacyRequests({requestId,ur=false,admitted=false}:{requestId?:string;ur?:boolean;admitted?:boolean}){
  const role=useAdminRole();
  return <div className={styles.screen} dir={ur?'rtl':'ltr'}><AdminPageContainer>
    <AdminPageHeader title={requestId?'Privacy Export Request':'Privacy Export Requests'} description="Review authorized export request metadata." actions={requestId&&<Link href={root} prefetch={false}>Back to Privacy Requests</Link>}/>
    {!canReviewPrivacy(role.authenticatedRoles)?<AdminEmptyState title="Access denied" description="Security Admin with verified MFA and case-bound authority is required. Role preview does not grant access."/>:
      !admitted?<AdminCard><section className={styles.body}><h2>Live Privacy integration disabled</h2><p>Metadata review is not yet available. No privacy records are loaded.</p><p>Export decisions and downloads are unavailable.</p></section></AdminCard>:
      <ExportRequests key={requestId??'list'} requestId={requestId}/>}
  </AdminPageContainer></div>;
}
function ExportRequests({requestId}:{requestId?:string}){
  const [data,setData]=useState<ExportPage|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [status,setStatus]=useState('all'),[reference,setReference]=useState(''),[limit,setLimit]=useState('20');
  const [cursors,setCursors]=useState<(string|null)[]>([null]),[index,setIndex]=useState(0);
  const generation=useRef(0),active=useRef<AbortController|null>(null),query=useRef(new URLSearchParams());
  const load=useCallback(async(q:URLSearchParams)=>{
    const n=++generation.current;active.current?.abort();const controller=new AbortController();active.current=controller;setBusy(true);setData(null);setError('');
    try{
      const safe=exportQuery(q);query.current=safe;
      const response=await fetch(root+'/api'+(safe.size?'?'+safe:''),{method:'GET',cache:'no-store',redirect:'error',signal:controller.signal});
      if(!response.ok)throw Error(String(response.status));
      const result=exportPage(await response.json(),safe);
      if(n===generation.current&&!controller.signal.aborted)setData(result);
    }catch(e){if(n===generation.current&&!controller.signal.aborted)setError(e instanceof Error&&['401','403'].includes(e.message)?'Access denied. Security Admin, verified MFA and current case authority are required.':'Privacy metadata unavailable. Refresh to try again.');}
    finally{if(n===generation.current)setBusy(false);}
  },[]);
  useEffect(()=>{
    try{
      if(requestId)exportId(requestId);
      const q=exportQuery(new URLSearchParams(window.location.search));setLimit(q.get('limit')??'20');setCursors([q.get('cursor')]);void load(q);
    }catch{setError('Invalid request reference or page query.');return;}
    const visibility=()=>{if(document.hidden){generation.current++;active.current?.abort();setData(null);setBusy(false);}else void load(query.current);};
    document.addEventListener('visibilitychange',visibility);
    return ()=>{generation.current++;active.current?.abort();document.removeEventListener('visibilitychange',visibility);};
  },[load,requestId]);
  const refresh=()=>{const q=new URLSearchParams(query.current);if(limit!==(q.get('limit')??'20')){q.delete('cursor');setCursors([null]);setIndex(0);}q.set('limit',limit);void load(q);};
  const items=(data?.items??[]).filter(row=>(!requestId||row.request_id===requestId.toLowerCase())&&(status==='all'||row.status===status)&&(!reference.trim()||row.request_id.toLowerCase().includes(reference.trim().toLowerCase())));
  function move(next:number){const q=new URLSearchParams(query.current);q.delete('cursor');if(cursors[next])q.set('cursor',cursors[next]!);setIndex(next);void load(q);}
  return <>
    <p className={styles.notice}>Only export metadata authorized for your current case authority is listed. This is not a general privacy or deletion queue. Request creation does not establish export completion.</p>
    {!requestId&&<AdminCard><div className={styles.toolbar}>
      <label>Status (this page)<select aria-label="Status (this page)" value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All statuses</option>{exportStates.map(state=><option key={state} value={state}>{state}</option>)}</select></label>
      <label>Request reference (this page)<input value={reference} maxLength={36} autoComplete="off" onChange={e=>setReference(e.target.value)}/></label>
      <button type="button" disabled={status==='all'&&!reference} onClick={()=>{setStatus('all');setReference('');}}>Clear filters</button>
    </div></AdminCard>}
    <AdminCard><form className={styles.toolbar} onSubmit={e=>{e.preventDefault();refresh();}}>
      <label>Page size<select aria-label="Page size" value={limit} disabled={busy} onChange={e=>setLimit(e.target.value)}>{[20,50,100].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
      <button disabled={busy}>Refresh requests</button><p>Status and reference filters apply only to the loaded page. No complete-directory total is available.</p>
    </form></AdminCard>
    {busy&&<p role="status">Loading privacy request metadata…</p>}{error&&<p role="alert">{error}</p>}
    {!busy&&!error&&data&&!items.length&&<AdminEmptyState title={requestId?'Request not present on this authorized page':'No export requests on this page'} description={requestId?'This does not prove the request is absent globally. Browse authorized pages or return to the request list.':'No records match this page and its local filters. Other pages may contain different statuses.'}/>}
    {!requestId&&data&&!!items.length&&<AdminCard><div className={styles.scroll} role="region" aria-label="Authorized privacy export requests" tabIndex={0}><table><thead><tr>{['Request ID','Case reference','Status','Revision','Scope','Created','Ready at','Expires at','Details'].map(label=><th key={label} scope="col">{label}</th>)}</tr></thead><tbody>{items.map(row=><tr key={row.request_id}><td className={styles.mono}>{row.request_id}</td><td className={styles.mono}>{row.case_id}</td><td><RequestStatus value={row.status}/></td><td>{row.revision}</td><td>{row.scope_version}</td><td>{row.created_at}</td><td>{row.ready_at??'—'}</td><td>{row.expires_at??'—'}</td><td><Link href={root+'/'+row.request_id+(query.current.size?'?'+query.current:'')} prefetch={false}>View details</Link></td></tr>)}</tbody></table></div><p className={styles.count}>{items.length} shown on this page; not a directory total.</p></AdminCard>}
    {requestId&&items.map(row=><AdminCard key={row.request_id}><section className={styles.body}><h2>Authorized request metadata</h2><dl className={styles.facts}><div><dt>Status</dt><dd><RequestStatus value={row.status}/></dd></div>{[['Request ID',row.request_id],['Case reference',row.case_id],['Revision',row.revision],['Scope',row.scope_version],['Created',row.created_at],['Ready at',row.ready_at],['Expires at',row.expires_at]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value??'—'}</dd></div>)}</dl><p>An updated timestamp is not supplied by this API. Case references do not grant access to case contents. A recorded ready status does not authorize a download.</p></section></AdminCard>)}
    {data&&<div className={styles.actions}><button disabled={busy||index===0} onClick={()=>move(index-1)}>Previous page</button><span>Page {index+1}{cursors[0]?' from linked cursor':''}</span><button disabled={busy||!data.next_cursor} onClick={()=>{const next=data.next_cursor!;setCursors([...cursors.slice(0,index+1),next]);setIndex(index+1);const q=new URLSearchParams(query.current);q.set('cursor',next);void load(q);}}>Next page</button></div>}
    <AdminCard><section className={styles.body}><h2>Actions unavailable</h2><p>Approvals, rejections and escalations are unavailable under the current review policy. This screen provides authorized metadata only. Case review permissions must be established separately.</p><p>Export contents, customer identity, download links and review notes are unavailable. No deletion workflow is provided.</p></section></AdminCard>
  </>;
}
