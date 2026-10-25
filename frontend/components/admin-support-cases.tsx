"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AdminCard, AdminEmptyState, AdminPageContainer, AdminPageHeader, AdminStatusBadge } from "./admin-ui";
import { useAdminRole } from "./admin-shell";
import { caseTypes, caseStatuses, casePriorities, fetchSupport, supportError, type CasePage, type CaseDetail, type CaseHistory } from "../lib/admin-support-metadata";
import styles from "./admin-support-cases.module.css";

const defaults = {case_id:"", case_type:"", status:"", priority:"", queue:"mine", limit:"20"};
function label(value: string) { return value.replaceAll("_", " "); }
function Status({value}: {value: string}) { return <AdminStatusBadge label={label(value)} variant={value === "resolved" ? "success" : value === "open" ? "info" : "neutral"}/>; }
export function AdminSupportCases({caseId, ur = false, admitted = false}: {caseId?: string; ur?: boolean; admitted?: boolean}) {
  const role = useAdminRole();
  // Prop is a server-supplied display gate, never a permission. The server relay
  // independently rejects all requests until governance admission is recorded.
  const permitted = admitted && role.authenticatedRoles.includes("support") && role.selectedRole === "authenticated";
  const [draft,setDraft] = useState(defaults), [filters,setFilters] = useState(defaults);
  const [cursor,setCursor] = useState<string | null>(null), [previous,setPrevious] = useState<(string | null)[]>([]);
  const [reload,setReload] = useState(0), [page,setPage] = useState<CasePage | null>(null), [detail,setDetail] = useState<CaseDetail | null>(null);
  const [busy,setBusy] = useState(permitted), [error,setError] = useState("");
  const [history,setHistory] = useState<CaseHistory | null>(null), [historyCursor,setHistoryCursor] = useState<string | null>(null);
  const [historyBusy,setHistoryBusy] = useState(false), [historyError,setHistoryError] = useState(""), [historyLoad,setHistoryLoad] = useState(false), [historyReload,setHistoryReload] = useState(0);
  useEffect(() => {
    if (!permitted) return;
    const controller = new AbortController(); let active = true;
    const timer = setTimeout(() => controller.abort(),15000);
    setBusy(true); setError(""); setPage(null); setDetail(null);
    setHistory(null); setHistoryError(""); setHistoryLoad(false); setHistoryCursor(null);
    const q = new URLSearchParams();
    if (!caseId) { for (const [k,v] of Object.entries(filters)) if (v) q.set(k,v); if (cursor) q.set("cursor",cursor); }
    void fetchSupport(caseId ? "detail" : "list",q,caseId,controller.signal).then(result => {
      if (active) { if (caseId) setDetail(result as CaseDetail); else setPage(result as CasePage); }
    }).catch(e => { if (active) setError(supportError(e)); }).finally(() => { clearTimeout(timer); if (active) setBusy(false); });
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  },[permitted,caseId,filters,cursor,reload]);
  useEffect(() => {
    if (!permitted || !historyLoad || !detail?.assigned_to_me || !caseId) return;
    const controller = new AbortController(); let active = true;
    const timer = setTimeout(() => controller.abort(),15000);
    setHistoryBusy(true); setHistoryError(""); setHistory(null);
    const q = new URLSearchParams({limit:"20"}); if (historyCursor) q.set("cursor",historyCursor);
    void fetchSupport("history",q,caseId,controller.signal).then(result => { if (active) setHistory(result as CaseHistory); }).catch(e => { if (active) setHistoryError(supportError(e)); }).finally(() => { clearTimeout(timer); if (active) setHistoryBusy(false); });
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  },[permitted,caseId,detail,historyLoad,historyCursor,historyReload]);
  const refresh = () => { setCursor(null); setPrevious([]); setReload(v => v+1); };
  return <div className={styles.screen} dir={ur ? "rtl" : "ltr"}><AdminPageContainer>
    <AdminPageHeader title={caseId ? "Support Case Details" : "Support Cases"} description="Authorized case metadata only" actions={caseId && <Link href="/admin/support" prefetch={false}>Back to Support Cases</Link>}/>
    {!admitted ? <AdminEmptyState title="Live Support integration disabled" description="Read-only frontend is prepared. Live authentication and database acceptance are pending; no cases are loaded."/> : !permitted ? <AdminEmptyState title="Access denied" description="Explicit authenticated Support access is required. Role preview does not grant access."/> : <>
      <p className={styles.notice}>Read-only metadata. Customer details, descriptions, internal notes and actor identities are unavailable.</p>
      {!caseId && <AdminCard><form className={styles.toolbar} onSubmit={e => { e.preventDefault(); setCursor(null); setPrevious([]); setFilters({...draft}); }}>
        <label>Exact case ID<input value={draft.case_id} onChange={e => setDraft({...draft,case_id:e.target.value})}/></label>
        {([['Case type','case_type',caseTypes],['Status','status',caseStatuses],['Priority','priority',casePriorities],['Queue','queue',['mine','unassigned','all']]] as const).map(([name,key,options]) => <label key={key}>{name}<select aria-label={name} value={draft[key]} onChange={e => setDraft({...draft,[key]:e.target.value})}>{key !== 'queue' && <option value="">All</option>}{options.map(v => <option key={v} value={v}>{v === 'all' ? 'Mine and unassigned' : label(v)}</option>)}</select></label>)}
        <label>Page size<select aria-label="Page size" value={draft.limit} onChange={e => setDraft({...draft,limit:e.target.value})}>{[20,50,100].map(n => <option key={n} value={n}>{n}</option>)}</select></label>
        <button type="submit" disabled={busy}>Apply filters</button><button type="button" disabled={busy} onClick={() => {setDraft(defaults); setFilters({...defaults}); setCursor(null); setPrevious([]);}}>Clear filters</button>
      </form></AdminCard>}
      <button type="button" disabled={busy} onClick={refresh}>Refresh cases</button>
      {busy && <p role="status">Loading case metadata…</p>}{error && <p role="alert">{error}</p>}
      {!busy && !error && page && <AdminCard>{page.items.length ? <div className={styles.scroll} role="region" aria-label="Authorized case metadata" tabIndex={0}><table><thead><tr>{['Case ID','Type','Status','Priority','Assignment','Revision','Created','Details'].map(v => <th scope="col" key={v}>{v}</th>)}</tr></thead><tbody>{page.items.map(item => <tr key={item.case_id}><td className={styles.mono}>{item.case_id}</td><td>{label(item.case_type)}</td><td><Status value={item.status}/></td><td>{item.priority}</td><td>{item.assigned_to_me ? 'Assigned to me' : 'Unassigned'}</td><td>{item.case_revision}</td><td><time dateTime={item.created_at}>{item.created_at}</time></td><td><Link href={'/admin/support/'+item.case_id} prefetch={false}>View details</Link></td></tr>)}</tbody></table></div> : <AdminEmptyState title="No cases found" description="No authorized cases match these filters."/>}
        <p className={styles.count}>Showing {page.items.length} cases on this page; this is not the complete case directory. As of {page.as_of}.</p>
      </AdminCard>}
      {!caseId && <div className={styles.actions}><button disabled={busy || previous.length === 0} onClick={() => {setCursor(previous.at(-1) ?? null); setPrevious(previous.slice(0,-1));}}>Previous</button><button disabled={busy || !page?.next_cursor} onClick={() => {setPrevious([...previous,cursor]); setCursor(page!.next_cursor);}}>Next</button></div>}
      {!busy && !error && detail && <>
        <AdminCard><section className={styles.body}><h2>Case metadata</h2><dl className={styles.facts}>{[['Case ID',detail.case_id],['Type',label(detail.case_type)],['Status',detail.status],['Priority',detail.priority],['Assignment',detail.assigned_to_me ? 'Assigned to me' : 'Unassigned'],['Revision',String(detail.case_revision)],['Created',detail.created_at]].map(([k,v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl><p>Case content is unavailable. Descriptions and internal notes are not provided by this contract.</p></section></AdminCard>
        <AdminCard><section className={styles.body}><h2>Case history</h2>{!detail.assigned_to_me ? <p>History is available only for cases assigned to you.</p> : <>
          <button disabled={historyBusy} onClick={() => {setHistoryLoad(true); setHistoryCursor(null); setHistoryReload(v => v+1);}}>{historyLoad ? 'Refresh history' : 'Load history'}</button>
          {historyBusy && <p role="status">Loading case history…</p>}{historyError && <p role="alert">{historyError}</p>}
          {history && <>{history.items.length ? <ol className={styles.history}>{history.items.map(e => <li key={e.event_id}><strong>{label(e.event_type)} · Revision {e.case_revision}</strong><p>{e.from_status ? label(e.from_status)+' → ' : ''}{label(e.to_status)} · {e.priority}</p><p>Event ID: {e.event_id}</p><time dateTime={e.created_at}>{e.created_at}</time></li>)}</ol> : <p>No recorded history on this page.</p>}<p>Case revision {history.case_revision}. Only recorded events are shown; gaps do not imply missing events.</p><button disabled={historyBusy || !history.next_cursor} onClick={() => setHistoryCursor(history.next_cursor)}>Older history</button></>}
        </>}</section></AdminCard>
      </>}
    </>}
    <AdminCard><section className={styles.body}><h2>Unavailable actions</h2><p>Case changes and financial decisions require separate approved contracts.</p><div className={styles.actions}>{['Create Case','Claim Case','Add Internal Note','Change Priority','Change Status','Financial Decision','QR-pair support operations'].map(v => <button type="button" disabled key={v}>{v}</button>)}</div></section></AdminCard>
  </AdminPageContainer></div>;
}
