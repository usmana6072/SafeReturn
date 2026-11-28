"use client";
import type { Design } from '../lib/admin-templates-contract';

export const selectedStickerDesign: Design = {
 schema_version:1,renderer:'safereturn-vector-v1',preset:'qr-only-v3',
 symbol_mm:'15.00',width_mm:'25.00',height_mm:'20.00',qr_x_mm:'5.00',qr_y_mm:'4.26',
 logo_mm:'2.00',min_pitch_mm:'0.30',font_pt:'5.00',header:'SafeReturn',
 english_lines:['SCAN TO CONTACT OWNER'],urdu_lines:['مالک سے رابطے کے لیے اسکین کریں'],
 asset_set_id:'70af0cb0-0cef-4d3a-a24a-f3cb0c81d5e4',material_codes:['vinyl'],
};

export function TemplateDesignFields({content,onChange,readOnly,purpose}:{content:string;onChange:(s:string)=>void;readOnly:boolean;purpose:'lost'|'ice'}) {
 let parsed:Partial<Design>={};let invalid=false;
 try{const p=JSON.parse(content);if(!p||typeof p!=='object'||Array.isArray(p))invalid=true;else parsed=p;}catch{invalid=true;}
 const assetSetId=typeof parsed.asset_set_id==='string'&&parsed.asset_set_id?parsed.asset_set_id:selectedStickerDesign.asset_set_id;
 function change(key:keyof Design,value:unknown){const next={schema_version:1,renderer:'safereturn-vector-v1',preset:parsed.preset??selectedStickerDesign.preset,...parsed,asset_set_id:parsed.asset_set_id??selectedStickerDesign.asset_set_id,[key]:value} as Design;if(next.preset==='qr-only-v3'&&key!=='qr_x_mm'&&key!=='qr_y_mm'){const english=Array.isArray(next.english_lines)?next.english_lines:[],urdu=Array.isArray(next.urdu_lines)?next.urdu_lines:[];next.english_lines=english;next.urdu_lines=urdu;const width=Number(next.width_mm),height=Number(next.height_mm),symbol=Number(next.symbol_mm),font=Number(next.font_pt),count=english.length+urdu.length;if([width,height,symbol,font].every(Number.isFinite)){next.qr_x_mm=((width-symbol)/2).toFixed(2);const low=.3+(count? .2:0)+count*font/2.8346456693,high=height-symbol-.5;next.qr_y_mm=(count&&high>=low?Math.min(high,Math.max(low+.02,(low+high)/2)):(height-symbol)/2).toFixed(2);}}onChange(JSON.stringify(next,null,2));}
 function setCaption(key:'english_lines'|'urdu_lines',enabled:boolean){const fallback=key==='english_lines'?'SCAN TO CONTACT OWNER':'مالک سے رابطے کے لیے اسکین کریں';change(key,enabled?(lines(key).length?lines(key):[fallback]):[]);}
 const text=(key:keyof Design)=>typeof parsed[key]==='string'?parsed[key] as string:'';
 const lines=(key:'english_lines'|'urdu_lines'|'material_codes')=>Array.isArray(parsed[key])&&parsed[key]!.every(v=>typeof v==='string')?parsed[key]!:[];
 const dimensions=[['width_mm','Sticker width (mm)'],['height_mm','Sticker height (mm)'],['symbol_mm','QR size (mm)'],['qr_x_mm','QR left position (mm)'],['qr_y_mm','QR bottom position (mm)'],['logo_mm','Logo size (mm)'],['font_pt','Text size (pt)'],['min_pitch_mm','Minimum QR module pitch (mm)']] as const;
 return <section aria-label="Sticker design" className="space-y-3">
 <p>Sticker and QR sizes are physical millimeters. The 25 × 20 mm minimum preset uses a 15 mm QR and automatically positions its captions. Longer copy may require a larger sticker.</p>
 {purpose==='lost'&&<button type="button" disabled={readOnly} onClick={()=>{if(content.trim()!=='{}'&&!window.confirm('Replace the current editor contents with the selected design?'))return;onChange(JSON.stringify(selectedStickerDesign,null,2));}}>Use selected 25 × 20 mm minimum design</button>}
 {purpose==='ice'&&<p>Enter reviewed emergency wording for ICE; the Lost return instructions are not an emergency design.</p>}
 {invalid?<p role="status">Advanced JSON is invalid. Correct it below or load the selected Lost design. Your text has been retained.</p>:<fieldset disabled={readOnly} className="grid gap-3 md:grid-cols-2"><legend>Sticker dimensions and text</legend>
 {dimensions.map(([key,label])=><label key={key}>{label}<input aria-label={label} inputMode="decimal" min={key==='width_mm'?(parsed.preset==='qr-only-v3'?25:30):key==='height_mm'?(parsed.preset==='qr-only-v3'?20:50):key==='symbol_mm'?(parsed.preset==='qr-only-v3'?15:20):key==='qr_x_mm'?(parsed.preset==='qr-only-v3'?0.5:4):key==='qr_y_mm'?(parsed.preset==='qr-only-v3'?0.3:13):key==='font_pt'?(parsed.preset==='qr-only-v3'?4.5:8):key==='min_pitch_mm'?0.3:undefined} max={key==='width_mm'?190:key==='height_mm'?270:key==='symbol_mm'?100:key==='font_pt'?14:undefined} step="0.01" value={typeof parsed[key]==='string'?parsed[key]:''} onChange={e=>change(key,e.target.value)}/></label>)}
 {parsed.preset!=='qr-only-v3'&&<label>Heading<input aria-label="Sticker heading" maxLength={50} value={text('header')} onChange={e=>change('header',e.target.value)}/></label>}
 <label>Sticker layout<select aria-label="Sticker layout" value={parsed.preset??selectedStickerDesign.preset} onChange={e=>change('preset',e.target.value)}><option value="fixed-footer-v1">Fixed footer · 12 mm header</option><option value="fixed-footer-v2">Compact footer · 8 mm header</option><option value="qr-only-v3">QR + optional captions · no header</option></select></label>
 <label><input type="checkbox" aria-label="Enable English caption" checked={lines('english_lines').length>0} onChange={e=>setCaption('english_lines',e.target.checked)}/> Enable English caption</label>
 <label><input type="checkbox" aria-label="Enable Urdu caption" checked={lines('urdu_lines').length>0} onChange={e=>setCaption('urdu_lines',e.target.checked)}/> Enable Urdu caption</label>
 {lines('english_lines').length>0&&<label>English caption (one line per row)<textarea aria-label="English sticker text" rows={2} value={lines('english_lines').join('\n')} onChange={e=>change('english_lines',e.target.value===''?[]:e.target.value.split('\n').filter(Boolean))}/></label>}
 {lines('urdu_lines').length>0&&<label>Urdu caption (one line per row)<textarea aria-label="Urdu sticker text (optional)" lang="ur" dir="rtl" rows={2} value={lines('urdu_lines').join('\n')} onChange={e=>change('urdu_lines',e.target.value===''?[]:e.target.value.split('\n').filter(Boolean))}/></label>}
 <label>Materials (comma separated)<input aria-label="Sticker materials" value={lines('material_codes').join(', ')} onChange={e=>change('material_codes',[...new Set(e.target.value.split(',').map(v=>v.trim()).filter(Boolean))].sort())}/></label>
 <label>Font and logo asset set<select aria-label="Font and logo asset set" value={assetSetId} onChange={e=>change('asset_set_id',e.target.value)}><option value={selectedStickerDesign.asset_set_id}>Amiri font + SafeReturn logo (enrolled development set)</option>{assetSetId!==selectedStickerDesign.asset_set_id&&<option value={assetSetId}>Current asset set ({assetSetId})</option>}</select></label>
 </fieldset>}
 <p className="text-sm">The new design uses the registered Icon Kitchen logo asset set and enrolled Amiri font. Template publication and physical print QA remain separate approval steps. Vinyl is a proposed material until tested.</p>
 </section>;
}
