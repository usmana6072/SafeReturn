'use client';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { parsePage, parseDetail, parseTotal, parseCommand, parseReceipt, uuid, reasons, type Action, type Command, type Detail, type Page, type Total, type Filters, type Receipt } from '../lib/users-contract';
import styles from './user-directory.module.css';
type Pending = { action: Action; body: Command; key: string };
class ReadError extends Error { constructor(public status:number, public code='SERVICE_UNAVAILABLE') { super('unavailable'); } }
const api='/admin/users/api';
async function responseJson(response:Response):Promise<unknown> {
  if (!response.ok) { let code='SERVICE_UNAVAILABLE'; try {const value=await response.json(); if (typeof value?.error?.code==='string') code=value.error.code;} catch {} throw new ReadError(response.status,code); }
  return response.json();
}
export function UserDirectory({id,ur,canSupport=false,canAudit=false}:{id?:string;ur:boolean;canSupport?:boolean;canAudit?:boolean}) {
  const t=(en:string,urdu:string)=>ur?urdu:en;
  const [draft,setDraft]=useState({user_id:'',email_verified:'',provider_access:'',limit:'20'});
  const [page,setPage]=useState<Page|null>(null),[total,setTotal]=useState<Total|null>(null),[detail,setDetail]=useState<Detail|null>(null);
  const [listStatus,setListStatus]=useState('loading'),[countStatus,setCountStatus]=useState('loading'),[notice,setNotice]=useState('');
  const [caseId,setCaseId]=useState(''),[action,setAction]=useState<Action|''>(''),[reason,setReason]=useState(''),[confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(false),[receipt,setReceipt]=useState<Receipt|null>(null),[retry,setRetry]=useState(false);
  const generation=useRef(0),controller=useRef<AbortController|null>(null),pending=useRef<Pending|null>(null),writing=useRef(false);
  const clearSensitive=useCallback(()=>{setPage(null);setTotal(null);setDetail(null);setReceipt(null);setCaseId('');setAction('');setReason('');setConfirmed(false);},[]);
  const denial=useCallback((status:number,code:string)=>{generation.current++;controller.current?.abort();clearSensitive();pending.current=null;setRetry(false);setNotice(code==='REAUTH_REQUIRED'?'reauth':status===401?'signin':'denied');setListStatus('denied');setCountStatus('denied');},[clearSensitive]);
  function showError(error:unknown) { if (error instanceof ReadError && [401,403].includes(error.status)) {denial(error.status,error.code);return true;} return false; }
  function selected():Filters {return {user_id:draft.user_id?uuid(draft.user_id.trim()):null,email_verified:draft.email_verified===''?null:draft.email_verified==='true',provider_access:draft.provider_access===''?null:draft.provider_access as Filters['provider_access']};}
  async function load(cursor?:string, keepReceipt=false) {
    if (writing.current) return;
    const current=++generation.current;controller.current?.abort();const abort=new AbortController();controller.current=abort;
    setNotice('');setPage(null);setTotal(null);setDetail(null);setConfirmed(false);setAction('');setReason('');if (!keepReceipt)setReceipt(null);setListStatus('loading');setCountStatus('loading');
    const valid=()=>current===generation.current&&!abort.signal.aborted;
    try {
      if (id) {
        const value=await fetch(api+'?kind=detail&user_id='+encodeURIComponent(id),{cache:'no-store',signal:abort.signal,redirect:'error'}).then(responseJson);
        const parsed=parseDetail(value,id);if(valid()){setDetail(parsed);setListStatus('ready');}return;
      }
      const f=selected(),params=new URLSearchParams();for(const [k,v]of Object.entries(f))if(v!==null)params.set(k,String(v));
      const list=new URLSearchParams(params);list.set('kind','list');list.set('limit',draft.limit);if(cursor)list.set('cursor',cursor);
      const count=new URLSearchParams(params);count.set('kind','count');
      await Promise.all([
        fetch(api+'?'+list,{cache:'no-store',signal:abort.signal,redirect:'error'}).then(responseJson).then(v=>{const parsed=parsePage(v,Number(draft.limit));if(valid()){setPage(parsed);setListStatus(parsed.items.length?'ready':'empty');}}).catch(e=>{if(showError(e))return;if(valid()){setPage(null);setListStatus('unavailable');}}),
        fetch(api+'?'+count,{cache:'no-store',signal:abort.signal,redirect:'error'}).then(responseJson).then(v=>{const parsed=parseTotal(v,f);if(valid()){setTotal(parsed);setCountStatus('ready');}}).catch(e=>{if(showError(e))return;if(valid()){setTotal(null);setCountStatus('unavailable');}}),
      ]);
    } catch(e) {if(showError(e))return;if(valid()){setDetail(null);setListStatus(e instanceof ReadError&&e.status===404?'notfound':'unavailable');if(!id){setTotal(null);setCountStatus('unavailable');setNotice('invalid');}}}
  }
  useEffect(()=>{void load();return()=>{generation.current++;controller.current?.abort();pending.current=null;};},[id]); // Read only; commands run solely from explicit event handlers.
  useEffect(()=>{function hidden(){if(document.visibilityState==='hidden'){generation.current++;controller.current?.abort();clearSensitive();setListStatus('stale');setCountStatus('stale');setNotice(writing.current?'unknown':'stale');}}document.addEventListener('visibilitychange',hidden);return()=>document.removeEventListener('visibilitychange',hidden);},[clearSensitive]);
  const state=detail?.application_suspension;
  const canCommand=state?.status==='ready'&&state.commands_available&&state.revision<2147483647&&listStatus==='ready'&&!busy;
  function invalidateDraft(next:typeof draft){generation.current++;controller.current?.abort();setDraft(next);clearSensitive();setListStatus('stale');setCountStatus('stale');setNotice('');}
  async function send(existing?:Pending) {
    if(!id||!canCommand||writing.current)return;
    let request:Pending;
    try {request=existing??{action:action as Action,body:parseCommand({case_id:caseId.trim(),expected_revision:state!.status==='ready'?state!.revision:0,reason_code:reason,confirmed},action as Action),key:crypto.randomUUID()};if(!request.action)throw Error();}
    catch {setNotice('invalid');return;}
    pending.current=request;writing.current=true;setBusy(true);setConfirmed(false);setNotice('');setReceipt(null);const current=++generation.current;
    setDetail(null);setListStatus('loading');
    try {
      const value=await fetch(api+'?kind='+request.action+'&user_id='+id,{method:'POST',cache:'no-store',redirect:'error',headers:{'Content-Type':'application/json','Idempotency-Key':request.key},body:JSON.stringify(request.body),signal:AbortSignal.timeout(12000)}).then(responseJson);
      const result=parseReceipt(value,request.action,id,request.body);
      pending.current=null;if(current!==generation.current)return;setRetry(false);setReceipt(result);setNotice('recorded');
      writing.current=false;setBusy(false);await load(undefined,true);if(generation.current===current+1)setNotice('recorded');
    } catch(e) {
      if(showError(e))return;
      if(current!==generation.current){setRetry(true);return;}
      setDetail(null);setListStatus('stale');setConfirmed(false);
      const known=e instanceof ReadError&&[400,404,409,412,422].includes(e.status);
      if(known){pending.current=null;setRetry(false);setNotice(e instanceof ReadError&&e.code==='STALE_VERSION'?'version':'authority');}
      else {setRetry(true);setNotice('unknown');}
    } finally {writing.current=false;setBusy(false);}
  }
  const messages:Record<string,string>={loading:t('Loading…','لوڈ ہو رہا ہے…'),empty:t('No accounts match these filters.','ان شرائط کے مطابق کوئی اکاؤنٹ نہیں۔'),unavailable:t('Information unavailable. No zero or active state is implied.','معلومات دستیاب نہیں۔ اس کا مطلب صفر یا فعال اکاؤنٹ نہیں۔'),notfound:t('Account not available.','اکاؤنٹ دستیاب نہیں۔'),stale:t('Information needs a fresh read before use.','استعمال سے پہلے معلومات تازہ کریں۔'),denied:t('Access denied. Previous information has been cleared.','رسائی کی اجازت نہیں۔ سابقہ معلومات ہٹا دی گئی ہیں۔')};
  const alerts:Record<string,string>={signin:t('Sign in again. Previous information has been cleared.','دوبارہ سائن ان کریں۔ سابقہ معلومات ہٹا دی گئی ہیں۔'),denied:messages.denied,reauth:t('Recent authentication is required. Step up, then reopen the account.','حالیہ تصدیق درکار ہے۔ تصدیق کے بعد اکاؤنٹ دوبارہ کھولیں۔'),stale:messages.stale,invalid:t('Review the case UUID, action, reason and explicit confirmation.','معاملے کی شناخت، کارروائی، وجہ اور واضح تصدیق کا جائزہ لیں۔'),unknown:t('Outcome unknown. Refresh and review; only retry the same confirmed request. If this page is reloaded, ask security to review before a new request.','نتیجہ نامعلوم ہے۔ معلومات تازہ کر کے جائزہ لیں؛ صرف اسی تصدیق شدہ درخواست کی دوبارہ کوشش کریں۔ صفحہ دوبارہ لوڈ ہونے پر نئی درخواست سے پہلے سکیورٹی جائزہ لیں۔'),version:t('Account revision changed. Refresh and obtain a new matching approval.','اکاؤنٹ کی معلومات بدل گئی ہیں۔ تازہ معلومات اور نئی موزوں منظوری حاصل کریں۔'),authority:t('Request was not accepted. Review case authority and current account information.','درخواست قبول نہیں ہوئی۔ معاملے کی اجازت اور تازہ اکاؤنٹ معلومات کا جائزہ لیں۔'),recorded:t('Operation receipt recorded. Current state must come from the refreshed account read.','کارروائی کی رسید درج ہو گئی ہے۔ موجودہ حالت تازہ اکاؤنٹ معلومات سے معلوم کریں۔')};
  function labelReason(code:string){const labels:Record<string,[string,string]>={suspected_compromise:['Suspected compromise','اکاؤنٹ تک غیر مجاز رسائی کا شبہ'],abuse_review:['Abuse review','غلط استعمال کا جائزہ'],security_review:['Security review','سکیورٹی جائزہ'],review_cleared:['Review cleared','جائزہ مکمل'],factor_loss:['Lost authentication factor','تصدیق کا ذریعہ گم ہو گیا'],account_access_review:['Account access review','اکاؤنٹ رسائی کا جائزہ']};return labels[code]?t(...labels[code]):'';}
  const actionLabel=(v:Action)=>v==='suspend'?t('Suspend account','اکاؤنٹ معطل کریں'):v==='restore'?t('Restore account access','اکاؤنٹ رسائی بحال کریں'):t('Record recovery referral','بازیابی کا حوالہ درج کریں');
  function metadata(u:Detail['user']){return <dl><dt>{t('Account UUID','اکاؤنٹ کی شناخت')}</dt><dd><bdi>{u.user_id}</bdi></dd><dt>{t('Registered','رجسٹریشن')}</dt><dd><time dir="ltr">{u.registered_at}</time></dd><dt>{t('Email verification','ای میل کی تصدیق')}</dt><dd>{u.email_verified?t('Verified','تصدیق شدہ'):t('Unverified','غیر تصدیق شدہ')}</dd><dt>{t('Provider restriction','فراہم کنندہ کی پابندی')}</dt><dd>{u.provider_access==='banned'?t('Restricted','پابندی موجود ہے'):t('No provider ban observed','فراہم کنندہ کی پابندی نظر نہیں آئی')}</dd></dl>;}
  return <main className={styles.console} dir={ur?'rtl':'ltr'}>
    <h1>{id?t('Account review','اکاؤنٹ کا جائزہ'):t('User directory','صارفین کی فہرست')}</h1>
    <p>{t('Limited account metadata. Provider restrictions are separate from application suspension.','اکاؤنٹ کی محدود معلومات۔ فراہم کنندہ کی پابندی، ایپ میں معطلی سے الگ ہے۔')}</p>
    {notice&&<p role="alert">{alerts[notice]??messages.unavailable}</p>}
    {['reauth','signin'].includes(notice)&&<Link href={notice==='signin'?'/login':'/admin/security/mfa?returnTo=%2Fadmin%2Fusers'} prefetch={false}>{t('Authenticate again','دوبارہ تصدیق کریں')}</Link>}
    <button type="button" disabled={busy} onClick={()=>void load()}>{t('Refresh account information','اکاؤنٹ معلومات تازہ کریں')}</button>
    {id?<Link href="/admin/users" prefetch={false}>{t('Back to directory','فہرست پر واپس جائیں')}</Link>:<>
      <form onSubmit={(e:FormEvent)=>{e.preventDefault();void load();}} className={styles.filters}>
        <label>{t('Exact account UUID','اکاؤنٹ کی مکمل شناخت')}<input name="user_id" value={draft.user_id} maxLength={36} dir="ltr" onChange={e=>invalidateDraft({...draft,user_id:e.target.value})}/></label>
        <label>{t('Email verification filter','ای میل تصدیق کی شرط')}<select aria-label={t('Email verification filter','ای میل تصدیق کی شرط')} value={draft.email_verified} onChange={e=>invalidateDraft({...draft,email_verified:e.target.value})}><option value="">{t('All','تمام')}</option><option value="true">{t('Verified','تصدیق شدہ')}</option><option value="false">{t('Unverified','غیر تصدیق شدہ')}</option></select></label>
        <label>{t('Provider restriction filter','فراہم کنندہ پابندی کی شرط')}<select aria-label={t('Provider restriction filter','فراہم کنندہ پابندی کی شرط')} value={draft.provider_access} onChange={e=>invalidateDraft({...draft,provider_access:e.target.value})}><option value="">{t('All','تمام')}</option><option value="banned">{t('Restricted','پابندی موجود ہے')}</option><option value="not_banned">{t('No provider ban','فراہم کنندہ کی پابندی نہیں')}</option></select></label>
        <label>{t('Page size','صفحے کا حجم')}<select aria-label={t('Page size','صفحے کا حجم')} value={draft.limit} onChange={e=>invalidateDraft({...draft,limit:e.target.value})}>{[20,50,100].map(n=><option key={n}>{n}</option>)}</select></label>
        <button type="submit">{t('Search / reset paging','تلاش / صفحات دوبارہ شروع کریں')}</button>
      </form>
      <section aria-label={t('Filtered registrations','شرائط کے مطابق رجسٹریشن')} aria-live="polite"><h2>{t('Matching registrations','شرائط کے مطابق رجسٹریشن')}</h2><p>{total?(total.count.is_exact?total.count.value:'1000+'):(messages[countStatus]??messages.unavailable)}</p><p>{t('Retained nonanonymous registrations, including unverified and provider-restricted accounts; deleted registrations are excluded. Current filtered observation, not an all-time total.','برقرار غیر گمنام رجسٹریشن، جن میں غیر تصدیق شدہ اور پابندی والے اکاؤنٹ شامل ہیں؛ حذف شدہ رجسٹریشن شامل نہیں۔ یہ موجودہ شرائط کا مشاہدہ ہے، ہمیشہ کی کل تعداد نہیں۔')}</p>{total&&<time dir="ltr">{total.as_of}</time>}</section>
    </>}
    <section aria-live="polite" aria-busy={listStatus==='loading'}><h2>{id?t('Observed account metadata','مشاہدہ شدہ اکاؤنٹ معلومات'):t('Directory results','فہرست کے نتائج')}</h2>
      {((!page&&!detail)||listStatus==='empty')&&<p>{messages[listStatus]??messages.unavailable}</p>}
      {page&&<><time dir="ltr">{page.as_of}</time>{page.items.map(u=><article key={u.user_id}>{metadata(u)}<Link href={'/admin/users/'+u.user_id} prefetch={false}>{t('Review account','اکاؤنٹ کا جائزہ لیں')}</Link></article>)}<button disabled={!page.next_cursor} onClick={()=>void load(page.next_cursor??undefined)}>{t('Next page','اگلا صفحہ')}</button></>}
      {detail&&<>{metadata(detail.user)}<time dir="ltr">{detail.as_of}</time><h3>{t('Application account state','ایپ میں اکاؤنٹ کی حالت')}</h3>{state?.status==='ready'?<><p>{state.state==='active'?t('Active','فعال'):t('Suspended','معطل')} · {t('Revision','نظرثانی')} {state.revision}</p><time dir="ltr">{state.as_of}</time>{!state.commands_available&&<p>{t('Account commands are unavailable.','اکاؤنٹ کی کارروائیاں دستیاب نہیں۔')}</p>}</>:<p>{messages.unavailable}</p>}</>}
    </section>
    {id&&<section aria-label={t('Case-approved actions','منظور شدہ معاملے کی کارروائیاں')}><h2>{t('Case-approved actions','منظور شدہ معاملے کی کارروائیاں')}</h2><p>{t('Case discovery is unavailable. Enter an existing authorized case reference. Independent approval, custody, recent authentication and self-action restrictions are checked by the server; this form grants no authority.','معاملات کی تلاش دستیاب نہیں۔ موجودہ مجاز معاملے کا حوالہ درج کریں۔ سرور آزاد منظوری، ذمہ داری، حالیہ تصدیق اور اپنے اکاؤنٹ پر کارروائی کی پابندیاں جانچتا ہے؛ یہ فارم اجازت نہیں دیتا۔')}</p>
      <p>{t('Recovery records a referral only. It does not change credentials, factors or email and sends no message. Restoration requires a fresh sign-in and does not restore revoked staff roles.','بازیابی صرف حوالہ درج کرتی ہے۔ اسناد، تصدیق کے ذرائع یا ای میل تبدیل نہیں ہوتے اور کوئی پیغام نہیں بھیجا جاتا۔ بحالی کے بعد نیا سائن ان ضروری ہے اور منسوخ عملے کے کردار بحال نہیں ہوتے۔')}</p>
      <form onSubmit={e=>{e.preventDefault();void send();}}><fieldset disabled={!canCommand||retry}><legend>{t('Review and confirm','جائزہ اور تصدیق')}</legend>
        <p><bdi>{id}</bdi></p><label>{t('Case UUID','معاملے کی شناخت')}<input dir="ltr" maxLength={36} value={caseId} onChange={e=>{setCaseId(e.target.value);setConfirmed(false);}}/></label>
        <label>{t('Action','کارروائی')}<select aria-label={t('Action','کارروائی')} value={action} onChange={e=>{setAction(e.target.value as Action);setReason('');setConfirmed(false);}}><option value="">{t('Choose action','کارروائی منتخب کریں')}</option>{(state?.status==='ready'?[state.state==='active'?'suspend':'restore','recovery']:[]) .map(v=><option key={v} value={v}>{actionLabel(v as Action)}</option>)}</select></label>
        <label>{t('Reason','وجہ')}<select aria-label={t('Reason','وجہ')} value={reason} onChange={e=>{setReason(e.target.value);setConfirmed(false);}}><option value="">{t('Choose reason','وجہ منتخب کریں')}</option>{action&&reasons[action].map(v=><option key={v} value={v}>{labelReason(v)}</option>)}</select></label>
        <label><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>{t('I confirm the displayed account, case, action and reason.','میں دکھائے گئے اکاؤنٹ، معاملے، کارروائی اور وجہ کی تصدیق کرتا ہوں۔')}</label>{(action||caseId)&&<p>{action&&actionLabel(action)} · <bdi>{caseId}</bdi></p>}
        <button type="submit" disabled={!confirmed||!action||!reason||!caseId||busy}>{busy?t('Submitting…','درخواست بھیجی جا رہی ہے…'):t('Submit confirmed request','تصدیق شدہ درخواست جمع کریں')}</button>
      </fieldset></form>
      {retry&&canCommand&&pending.current&&<p>{actionLabel(pending.current.action)} · <bdi>{pending.current.body.case_id}</bdi></p>}
      {retry&&<button type="button" disabled={!canCommand} onClick={()=>{if(pending.current)void send(pending.current);}}>{t('Retry same confirmed request','اسی تصدیق شدہ درخواست کی دوبارہ کوشش کریں')}</button>}
      {receipt&&<section aria-label={t('Operation receipt','کارروائی کی رسید')}><h3>{t('Operation receipt — not current state','کارروائی کی رسید — موجودہ حالت نہیں')}</h3><p><bdi>{receipt.event_id}</bdi></p><p>{t('Case reference','معاملے کا حوالہ')}: <bdi>{receipt.case_id}</bdi></p><time dir="ltr">{receipt.occurred_at}</time>{receipt.action==='recovery_escalated'&&<p>{t('Referral recorded; no account recovery or delivery performed.','حوالہ درج ہو گیا؛ اکاؤنٹ کی بازیابی یا ترسیل نہیں ہوئی۔')}</p>}</section>}
      {canSupport&&<Link href="/admin/support" prefetch={false}>{t('Support workspace','معاونت کی کام کی جگہ')}</Link>}{canAudit&&<Link href="/admin/audit" prefetch={false}>{t('Audit search','آڈٹ تلاش')}</Link>}
    </section>}
  </main>;
}
