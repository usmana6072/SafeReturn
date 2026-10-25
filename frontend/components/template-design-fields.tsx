"use client";
import type { Design } from '../lib/admin-templates-contract';

export const selectedStickerDesign: Design = {
 schema_version:1,renderer:'safereturn-vector-v1',preset:'fixed-footer-v1',
 symbol_mm:'30.00',width_mm:'40.00',height_mm:'60.00',qr_x_mm:'5.00',qr_y_mm:'18.00',
 logo_mm:'4.00',min_pitch_mm:'0.30',font_pt:'8.00',header:'SafeReturn',
 english_lines:['Found? Scan me.'],urdu_lines:['ملا ہے؟ اسکین کریں'],
 asset_set_id:'0a7c508b-fc96-42d6-ba58-e367dbb8d08b',material_codes:['vinyl'],
};

export function TemplateDesignFields({content,onChange,readOnly,purpose}:{content:string;onChange:(s:string)=>void;readOnly:boolean;purpose:'lost'|'ice'}) {
 let parsed:Partial<Design>={};let invalid=false;
 try{const p=JSON.parse(content);if(!p||typeof p!=='object'||Array.isArray(p))invalid=true;else parsed=p;}catch{invalid=true;}
 function change(key:keyof Design,value:unknown){onChange(JSON.stringify({schema_version:1,renderer:'safereturn-vector-v1',preset:'fixed-footer-v1',...parsed,[key]:value},null,2));}
 const text=(key:keyof Design)=>typeof parsed[key]==='string'?parsed[key] as string:'';
 const lines=(key:'english_lines'|'urdu_lines'|'material_codes')=>Array.isArray(parsed[key])&&parsed[key]!.every(v=>typeof v==='string')?parsed[key]!:[];
 const dimensions=[['width_mm','Sticker width (mm)'],['height_mm','Sticker height (mm)'],['symbol_mm','QR size (mm)'],['qr_x_mm','QR left position (mm)'],['qr_y_mm','QR bottom position (mm)'],['logo_mm','Logo size (mm)'],['font_pt','Text size (pt)'],['min_pitch_mm','Minimum QR module pitch (mm)']] as const;
 return <section aria-label="Sticker design" className="space-y-3">
 <p>Set the whole sticker size separately from the QR size. Server validation, review and publication rules still apply.</p>
 {purpose==='lost'&&<button type="button" disabled={readOnly} onClick={()=>{if(content.trim()!=='{}'&&!window.confirm('Replace the current editor contents with the selected design?'))return;onChange(JSON.stringify(selectedStickerDesign,null,2));}}>Use selected 40 × 60 mm design</button>}
 {purpose==='ice'&&<p>Enter reviewed emergency wording for ICE; the Lost return instructions are not an emergency design.</p>}
 {invalid?<p role="status">Advanced JSON is invalid. Correct it below or load the selected Lost design. Your text has been retained.</p>:<fieldset disabled={readOnly} className="grid gap-3 md:grid-cols-2"><legend>Sticker dimensions and text</legend>
 {dimensions.map(([key,label])=><label key={key}>{label}<input aria-label={label} inputMode="decimal" value={typeof parsed[key]==='string'?parsed[key]:''} onChange={e=>change(key,e.target.value)}/></label>)}
 <label>Heading<input aria-label="Sticker heading" maxLength={50} value={text('header')} onChange={e=>change('header',e.target.value)}/></label>
 <label>English text (one line per row)<textarea aria-label="English sticker text" rows={2} value={lines('english_lines').join('\n')} onChange={e=>change('english_lines',e.target.value.split('\n'))}/></label>
 <label>Urdu text (one line per row)<textarea aria-label="Urdu sticker text" dir="rtl" rows={2} value={lines('urdu_lines').join('\n')} onChange={e=>change('urdu_lines',e.target.value.split('\n'))}/></label>
 <label>Materials (comma separated)<input aria-label="Sticker materials" value={lines('material_codes').join(', ')} onChange={e=>change('material_codes',[...new Set(e.target.value.split(',').map(v=>v.trim()).filter(Boolean))].sort())}/></label>
 <label>Enrolled font/logo asset set<input aria-label="Enrolled asset set ID" value={text('asset_set_id')} onChange={e=>change('asset_set_id',e.target.value)}/></label>
 </fieldset>}
 <p className="text-sm">The selected development asset set uses Amiri and the solid-colour logo. This is asset registration, not template or physical QA approval. Vinyl is a proposed material until tested.</p>
 </section>;
}
