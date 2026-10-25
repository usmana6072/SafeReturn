"use client";

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from './admin-ui';
import { useAdminRole } from './admin-shell';
import { canReadNotifications, notificationId as parseId, notificationPage, notificationQuery, notificationReceipt, notificationRetry, notificationStatuses, outboxChannel, type NotificationPage, type OutboxEvent, type RetryInput, type RetryReason } from '../lib/admin-notification-contract';
import styles from './admin-notifications.module.css';

type Props = {notificationId?:string; ur?:boolean; admitted?:boolean; retryAdmitted?:boolean};
const labels:Record<string,string> = {pending:'Pending',leased:'Leased',retry:'Retry scheduled',sent:'Provider accepted',dead:'Failed (dead)'};
export function NotificationStatusBadge({status}:{status?:string}) {
  return <AdminStatusBadge label={labels[status??'']??'Unknown state'} variant={status==='dead'?'danger':status==='pending'||status==='retry'?'warning':status==='sent'||status==='leased'?'info':'neutral'}/>;
}
export function AdminNotifications({notificationId,ur=false,admitted=false,retryAdmitted=false}:Props) {
  const role=useAdminRole();
  const title=notificationId?'Notification Details':'Notifications';
  return <div className={styles.screen} dir={ur?'rtl':'ltr'}><AdminPageContainer>
    <AdminPageHeader title={title} description="Review notification outbox metadata and recorded attempts." actions={notificationId&&<Link href="/admin/notifications" prefetch={false}>Back to Notifications</Link>}/>
    {!canReadNotifications(role.authenticatedRoles)?<AdminEmptyState title="Access denied" description="Operations or Security Admin with verified MFA is required. Role preview does not grant access."/>:
      !admitted?<AdminCard><section className={styles.body}><h2>Live Notifications integration disabled</h2><p>Backend acceptance is pending. No notification records are loaded.</p><p>Retry is unavailable until its delivery controls are accepted.</p></section></AdminCard>:
      <NotificationOutbox key={notificationId??'list'} notificationId={notificationId} retryAdmitted={retryAdmitted}/>}
  </AdminPageContainer></div>;
}
function NotificationOutbox({notificationId,retryAdmitted}:{notificationId?:string;retryAdmitted:boolean}) {
  const [data,setData]=useState<NotificationPage|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [status,setStatus]=useState(''),[channel,setChannel]=useState('all'),[exactId,setExactId]=useState('');
  const [cursors,setCursors]=useState<(string|null)[]>([null]),[index,setIndex]=useState(0);
  const [dialog,setDialog]=useState<OutboxEvent|null>(null),[reason,setReason]=useState<RetryReason>('provider_recovered'),[confirmed,setConfirmed]=useState(false);
  const [pending,setPending]=useState<RetryInput|null>(null),[unknown,setUnknown]=useState(false),[sending,setSending]=useState(false);
  const version=useRef(0),active=useRef<AbortController|null>(null),query=useRef(new URLSearchParams());
  const cancelButton=useRef<HTMLButtonElement|null>(null),dialogPanel=useRef<HTMLElement|null>(null),opener=useRef<HTMLElement|null>(null);
  const load=useCallback(async (q:URLSearchParams)=>{
    const n=++version.current;active.current?.abort();const controller=new AbortController();active.current=controller;
    setData(null);setError('');setBusy(true);
    try{
      const safe=notificationQuery(q);query.current=safe;
      const response=await fetch('/admin/notifications/api'+(safe.size?'?'+safe:''),{method:'GET',cache:'no-store',redirect:'error',signal:controller.signal});
      if(!response.ok)throw Error(String(response.status));
      const page=notificationPage(await response.json(),safe);
      if(n===version.current&&!controller.signal.aborted)setData(page);
    }catch(e){if(n===version.current&&!controller.signal.aborted)setError(e instanceof Error&&['401','403'].includes(e.message)?'Access denied. Sign in with Operations or Security Admin and verified MFA.':'Notification metadata unavailable. Refresh to try again.');}
    finally{if(n===version.current)setBusy(false);}
  },[]);
  useEffect(()=>{
    const q=new URLSearchParams();
    if(notificationId){try{q.set('id',parseId(notificationId));}catch{setError('Notification not found.');return;}}
    void load(q);
    const visibility=()=>{if(document.hidden){version.current++;active.current?.abort();setData(null);setBusy(false);}else void load(query.current);};
    document.addEventListener('visibilitychange',visibility);
    return ()=>{version.current++;active.current?.abort();document.removeEventListener('visibilitychange',visibility);};
  },[load,notificationId]);
  useEffect(()=>{
    if(!dialog)return;cancelButton.current?.focus();
    return ()=>opener.current?.focus();
  },[dialog]);
  const baseQuery=()=>{const q=new URLSearchParams();if(exactId.trim())q.set('id',exactId.trim());else if(status)q.set('status',status);return q;};
  function applyFilters(clear=false){
    if(pending||sending)return;
    setIndex(0);setCursors([null]);setNotice('');
    if(clear){setStatus('');setChannel('all');setExactId('');void load(new URLSearchParams());}
    else{try{void load(notificationQuery(baseQuery()));}catch{setData(null);setError('Invalid filters. Enter a complete notification UUID.');}}
  }
  function move(nextIndex:number){const q=new URLSearchParams(query.current);q.delete('cursor');const next=cursors[nextIndex];if(next)q.set('cursor',next);setIndex(nextIndex);void load(q);}
  function openRetry(event:OutboxEvent){opener.current=document.activeElement as HTMLElement;setDialog(event);setConfirmed(false);setReason('provider_recovered');setNotice('');}
  async function submitRetry(){
    if(!dialog||!confirmed||sending||!retryAdmitted)return;
    const input=pending??notificationRetry({id:dialog.id,key:crypto.randomUUID(),body:{expected_attempt_count:dialog.attempt_count,reason,confirmed:true}});
    setPending(input);setSending(true);setNotice('');setError('');
    try{
      const response=await fetch('/admin/notifications/api',{method:'POST',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(15000),headers:{'Content-Type':'application/json'},body:JSON.stringify(input)});
      if(!response.ok){
        if([400,404,409,412,422,429].includes(response.status)){
          setPending(null);setUnknown(false);setDialog(null);setConfirmed(false);await load(query.current);
          setNotice(response.status===412?'Retry refused: attempt count changed. Review the refreshed notification.':'Retry refused. Review current eligibility before confirming a new request.');return;
        }
        if([401,403].includes(response.status))setData(null);
        throw Error();
      }
      if(response.status!==202)throw Error();notificationReceipt(await response.json(),input);
      setPending(null);setUnknown(false);setDialog(null);setConfirmed(false);await load(query.current);
      setNotice('Retry queued. This receipt does not confirm email delivery.');
    }catch{setUnknown(true);setNotice('Outcome unavailable. Reconcile only this identical request with its original key; no automatic retry. If access is lost, obtain an authorized review.');}
    finally{setSending(false);}
  }
  const items=(data?.items??[]).filter(e=>channel==='all'||outboxChannel(e)===channel);
  const detail=notificationId!==undefined||query.current.has('id');
  return <>
    <p className={styles.notice}>Provider acceptance is separate from inbox delivery and physical item return. Recipients, message content and provider identifiers are not exposed.</p>
    {!notificationId&&<AdminCard><form className={styles.toolbar} onSubmit={e=>{e.preventDefault();applyFilters();}}>
      <label>Status<select aria-label="Status" value={status} disabled={!!pending||busy||!!exactId.trim()} onChange={e=>setStatus(e.target.value)}><option value="">All statuses</option>{notificationStatuses.map(s=><option key={s} value={s}>{labels[s]}</option>)}</select></label>
      <label>Channel (this page)<select aria-label="Channel (this page)" value={channel} onChange={e=>setChannel(e.target.value)}><option value="all">All channels</option><option value="email">Email (finder events)</option><option value="unavailable">Not provided</option></select></label>
      <label>Exact notification ID<input value={exactId} maxLength={36} disabled={!!pending||busy} onChange={e=>setExactId(e.target.value)} autoComplete="off"/></label>
      <button disabled={busy||!!pending}>Apply filters</button><button type="button" disabled={busy||!!pending} onClick={()=>applyFilters(true)}>Clear filters</button>
    </form></AdminCard>}
    <div className={styles.toolbar}><button disabled={busy||sending||!!pending} onClick={()=>{setIndex(0);setCursors([null]);const q=new URLSearchParams(query.current);q.delete('cursor');q.delete('attempt_before');void load(q);}}>Refresh notifications</button><span>Channel is derived only for supported finder email events. Channel filtering applies to the loaded page.</span></div>
    {busy&&<p role="status">Loading notifications…</p>}{error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
    {!busy&&!error&&data&&!items.length&&<AdminEmptyState title={detail?'Notification not found':'No notifications found'} description="No records match the current page and filters."/>}
    {!detail&&!busy&&data&&!!items.length&&<AdminCard><div className={styles.scroll} role="region" aria-label="Notification outbox" tabIndex={0}><table><thead><tr>{['Notification ID','Event','Status','Channel','Attempts','Created','Provider accepted','Details'].map(label=><th key={label}>{label}</th>)}</tr></thead><tbody>{items.map(event=><tr key={event.id}><td className={styles.mono}>{event.id}</td><td>{event.event_type}</td><td><NotificationStatusBadge status={event.status}/></td><td>{outboxChannel(event)==='email'?'Email (finder event)':'Not provided'}</td><td>{event.attempt_count}</td><td><time dateTime={event.created_at}>{event.created_at}</time></td><td>{event.sent_at??'—'}</td><td><Link href={'/admin/notifications/'+event.id} prefetch={false}>View details</Link></td></tr>)}</tbody></table></div><p className={styles.count}>{items.length} shown on this page; not an outbox total.</p></AdminCard>}
    {!detail&&data&&<div className={styles.toolbar}><button disabled={busy||index===0||!!pending} onClick={()=>move(index-1)}>Previous</button><span>Page {index+1}</span><button disabled={busy||!data.next_cursor||!!pending} onClick={()=>{const next=[...cursors.slice(0,index+1),data.next_cursor];setCursors(next);const q=new URLSearchParams(query.current);q.set('cursor',data.next_cursor!);setIndex(index+1);void load(q);}}>Next</button></div>}
    {detail&&items.map(event=><AdminCard key={event.id}><section className={styles.body}><h2>Delivery activity</h2><dl className={styles.facts}><div><dt>Notification ID</dt><dd className={styles.mono}>{event.id}</dd></div><div><dt>Status</dt><dd><NotificationStatusBadge status={event.status}/></dd></div>{[['Event',event.event_type],['Channel',outboxChannel(event)==='email'?'Email (finder event)':'Not provided'],['Attempt count',event.attempt_count],['Created',event.created_at],['Provider accepted',event.sent_at],['First attempt',event.first_attempt_at],['Next attempt',event.next_attempt_at],['Lease expires',event.lease_until],['Safe failure code',event.last_error_code],['Seconds overdue',event.due_lag_seconds]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value??'—'}</dd></div>)}</dl>
      <h2>Attempt history</h2>{event.attempts?.length?<ol className={styles.history}>{event.attempts.map(a=><li key={a.attempt_number}><strong>Attempt {a.attempt_number} · {a.outcome==='success'?'Provider accepted':a.outcome}</strong><p>{a.attempted_at} · Finished: {a.finished_at??'—'} · {a.error_code??'No recorded failure code'}</p></li>)}</ol>:<p>No recorded attempts on this page.</p>}
      {event.next_attempt_before&&<button disabled={busy||!!pending} onClick={()=>{const q=new URLSearchParams(query.current);q.set('attempt_before',String(event.next_attempt_before));void load(q);}}>Older attempts</button>}
      <h2>Reviewed retry</h2><p>{!retryAdmitted?'Retry disabled: live mutation acceptance is pending.':event.retry_blocked_reason?'Retry unavailable: '+event.retry_blocked_reason:'Review eligibility before queuing one additional attempt.'}</p>
      <button disabled={!retryAdmitted||event.status!=='dead'||event.retry_blocked_reason!==null||busy||!!pending} onClick={()=>openRetry(event)}>Review single-event retry</button>
    </section></AdminCard>)}
    {data&&<AdminCard><details className={styles.body}><summary>Template metadata</summary><p>Current template: {data.current_template.identifier}</p><p>Current code fingerprint: <span className={styles.mono}>{data.current_template.fingerprint}</span></p><p>Historical template versions were not recorded. Current metadata does not establish which template was sent.</p></details></AdminCard>}
    {dialog&&<section ref={dialogPanel} className={styles.dialog} role="dialog" aria-modal="true" aria-labelledby="notification-retry-title" onKeyDown={e=>{
      if(e.key==='Escape'&&!pending&&!sending){e.preventDefault();setDialog(null);}
      if(e.key==='Tab'){const controls=dialogPanel.current?.querySelectorAll<HTMLElement>('button:not(:disabled),select:not(:disabled),input:not(:disabled)');if(!controls?.length)return;const first=controls[0],last=controls[controls.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}
    }}><div className={styles.body}><h2 id="notification-retry-title">Confirm single-event retry</h2><p>{dialog.id} · Expected attempt count: {dialog.attempt_count}</p><p>This queues another attempt and may send an email. It does not confirm delivery.</p>
      <label>Reviewed reason<select aria-label="Reviewed reason" value={reason} disabled={!!pending||sending} onChange={e=>setReason(e.target.value as RetryReason)}><option value="provider_recovered">Provider recovered</option><option value="recipient_reverified">Recipient eligibility reverified</option></select></label>
      <label><input type="checkbox" checked={confirmed} disabled={!!pending||sending} onChange={e=>setConfirmed(e.target.checked)}/>I reviewed the failure and eligibility. Queue this single event.</label>
      <button ref={cancelButton} disabled={!!pending||sending} onClick={()=>setDialog(null)}>Cancel</button><button disabled={!confirmed||sending} onClick={()=>void submitRetry()}>{sending?'Submitting…':unknown?'Reconcile identical request':'Queue reviewed retry'}</button>
      {unknown&&<p role="alert">The outcome is unknown. Reason, attempt count and idempotency key are frozen; no automatic resend occurs.</p>}
    </div></section>}
  </>;
}
