"use client";
import { useCallback, useEffect, useRef, useState } from 'react';
import { choiceId, parseTemplateChoices, templatePath, type TemplateChoices } from '../lib/catalog-template-choices';

export function useTemplateChoices(enabled: boolean, editor: number) {
  const [state,setState] = useState<{mode:'idle'|'loading'|'ready'|'stale'|'unavailable'; data:TemplateChoices|null}>({mode:'idle',data:null});
  const sequence = useRef(0);
  const expiry = useRef<ReturnType<typeof setTimeout>|null>(null);
  const received = useRef(0);
  const refresh = useCallback(async () => {
    if (!enabled) return null;
    const request = ++sequence.current;
    if (expiry.current) clearTimeout(expiry.current);
    setState(old=>({...old,mode:'loading'}));
    try {
      const response = await fetch('/admin/catalog-api?path='+templatePath,{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(15000)});
      if (!response.ok) throw new Error('unavailable');
      const data = parseTemplateChoices(await response.json());
      if (request!==sequence.current) return null;
      received.current = performance.now();
      setState({mode:'ready',data});
      expiry.current=setTimeout(()=>setState(old=>({...old,mode:'stale'})),60000);
      return data;
    } catch {
      if (request===sequence.current) setState(old=>({...old,mode:'unavailable'}));
      return null;
    }
  },[enabled]);
  useEffect(()=>{
    if (enabled) void refresh();
    else setState({mode:'idle',data:null});
    return ()=>{++sequence.current;if(expiry.current)clearTimeout(expiry.current);};
  },[enabled,editor,refresh]);
  useEffect(()=>{
    const visible=()=>{if(enabled&&document.visibilityState==='visible')void refresh();};
    document.addEventListener('visibilitychange',visible);
    window.addEventListener('focus',visible);
    return ()=>{document.removeEventListener('visibilitychange',visible);window.removeEventListener('focus',visible);};
  },[enabled,refresh]);
  const fresh = state.mode==='ready' && performance.now()-received.current<60000;
  return {...state, fresh,refresh};
}

type ChoiceState = ReturnType<typeof useTemplateChoices>;
export function CatalogTemplatePicker({state,templateKey,version,canClear,busy,onChange,ur}:{state:ChoiceState;templateKey:string|null;version:number;canClear:boolean;busy:boolean;onChange:(key:string|null,version:number)=>void;ur:boolean}) {
  const selected=templateKey?choiceId({template_key:templateKey,template_version:version}):'';
  const listed=state.fresh&&state.data?.items.some(i=>choiceId(i)===selected);
  const message=state.mode==='loading' ? (ur?'ٹیمپلیٹس لوڈ ہو رہے ہیں۔':'Loading published templates…') : state.mode==='unavailable' ? (ur?'ٹیمپلیٹس کی فہرست دستیاب نہیں۔ دوبارہ کوشش کریں؛ اندراج برقرار ہے۔':'Template list unavailable. Retry; your entries remain.') : !state.fresh ? (ur?'فہرست پرانی ہے۔ انتخاب سے پہلے تازہ کریں۔':'Template list is stale. Refresh before choosing.') : !state.data?.items.length ? (ur?'کوئی کیٹلاگ ٹیمپلیٹ ترتیب نہیں دیا گیا۔':'No published or configured templates are available.') : (ur?'ترتیب شدہ ٹیمپلیٹس دستیاب ہیں۔':'Published templates and configured references available.');
  return <section aria-label={ur?'کیٹلاگ ٹیمپلیٹ کا انتخاب':'Catalog template selection'}>
    <p>{ur?'ترتیب شدہ کیٹلاگ ٹیمپلیٹس — رینڈرر اور اصل پرنٹ کی جانچ الگ ہیں۔':'Published templates and configured references — product assignment and rendering checks are separate.'}</p>
    <p role="status" aria-live="polite">{message}</p>
    <label htmlFor="catalog-template-choice">{ur?'کیٹلاگ ٹیمپلیٹ':'Catalog template'}</label>
    <select id="catalog-template-choice" aria-describedby="catalog-template-help" disabled={busy||!state.fresh||!state.data?.items.length} value={listed?selected:''} onChange={e=>{const item=state.data?.items.find(i=>choiceId(i)===e.target.value);if(item&&state.fresh)onChange(item.template_key,item.template_version);}}>
      <option value="" disabled>{ur?'ٹیمپلیٹ منتخب کریں':'Choose a template'}</option>
      {state.fresh&&state.data?.items.map(i=><option key={choiceId(i)} value={choiceId(i)}>{choiceId(i)}</option>)}
    </select>
    <p id="catalog-template-help">{ur?'انتخاب شناخت اور ورژن دونوں مقرر کرتا ہے؛ یہ پرنٹ یا اشاعت کی منظوری نہیں۔':'Selection sets both key and version; it does not grant print or publication approval.'}</p>
    {selected&&<p>{listed?(ur?'منتخب شناخت اور ورژن: ':'Selected key and version: '):(ur?'محفوظ یا منتخب قدر موجودہ فہرست میں تصدیق شدہ نہیں: ':'Saved or selected reference is not confirmed in the current list: ')}<bdi>{selected}</bdi></p>}
    <button type="button" className="button secondary" disabled={busy||state.mode==='loading'} onClick={()=>void state.refresh()}>{ur?'ٹیمپلیٹس تازہ کریں':'Refresh templates'}</button>
    {canClear&&templateKey&&<button type="button" className="button secondary" disabled={busy} onClick={()=>onChange(null,version)}>{ur?'ڈرافٹ کا ٹیمپلیٹ صاف کریں':'Clear draft template'}</button>}
    <p>{ur?'ڈرافٹ مصنوعہ کا نیا ویریئنٹ بغیر ٹیمپلیٹ محفوظ ہو سکتا ہے۔ ورژن 1 بذاتِ خود منظوری نہیں۔':'A new variant on a draft product can be saved without a template. Default version 1 is not an approval.'}</p>
  </section>;
}
