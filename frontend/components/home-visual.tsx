import type {ReactNode} from "react";
export function HomeIcon({name}:{name:"tag"|"medical"|"shield"|"arrow"|"check"|"bag"|"profile"|"layers"|"scan"}){
 const icons:Record<string,ReactNode>={
 tag:<><path d="m3 4 7-1 11 11-7 7L3 10Z"/><circle cx="7" cy="7" r="1"/></>,
 medical:<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6Z"/>,
 shield:<><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/></>,
 arrow:<path d="M4 12h16m-6-6 6 6-6 6"/>,
 check:<path d="m5 12 4 4L19 6"/>,
 bag:<><path d="M4 8h16l1 13H3ZM8 8V6a4 4 0 0 1 8 0v2"/></>,
 profile:<><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 6 0 0 1 16 0"/></>,
 layers:<><path d="m12 3 10 6-10 6L2 9ZM2 14l10 6 10-6M2 18l10 6 10-6"/></>,
 scan:<><path d="M8 3H3v5m13-5h5v5M3 16v5h5m8 0h5v-5M3 12h18"/></>
 };
 return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{icons[name]}</svg>;
}
export function DecorativeQr(){
 // Decorative geometry, deliberately not an encoded or activatable QR identity.
 return <svg className="home-qr-art" viewBox="0 0 100 100" aria-hidden="true" focusable="false" fill="currentColor"><path fillRule="evenodd" d="M5 5h27v27H5Zm5 5v17h17V10ZM68 5h27v27H68Zm5 5v17h17V10ZM5 68h27v27H5Zm5 5v17h17V73Z"/><path d="M15 15h7v7h-7Zm63 0h7v7h-7ZM15 78h7v7h-7ZM43 8h6v11h-6Zm10 15h8v9h-8ZM40 39h12v8H40Zm19-2h8v15h-8ZM76 43h17v7H76ZM7 43h20v7H7Zm8 12h8v6h-8ZM39 57h9v17h-9Zm17 6h10v8H56Zm21-6h7v14h-7ZM88 76h7v19h-7ZM56 82h13v7H56Zm-15 5h7v8h-7ZM72 87h8v8h-8Z"/></svg>;
}
export function HomeVisual({lost,ice,label,scan,share,note,illustration}:{lost:string;ice:string;label:string;scan:string;share:string;note:string;illustration:string}){
 return <figure className="home-visual" aria-label={illustration}><div className="home-visual-stage"><span className="home-visual-kicker"><span/>{label}</span>
 <svg className="home-bag-art" viewBox="0 0 360 390" fill="none" aria-hidden="true"><ellipse cx="178" cy="363" rx="144" ry="14" fill="#352525" opacity=".07"/><path d="M90 95h179l33 226c2 19-7 29-25 29H77c-18 0-27-10-24-29Z" fill="#d9c4b5"/><path d="M111 102V72c0-36 26-54 66-54s67 18 67 54v30" stroke="#864431" strokeWidth="20"/><path d="M98 98h159l16 244H73Z" fill="#e6d6c8"/><path d="M89 120h173M108 111l-5 228M249 111l8 228" stroke="#c8b3a3" strokeWidth="2"/><path d="m75 283 16-160 8-18M278 283l-17-160-8-18" stroke="#bfaaa0" strokeWidth="2"/><rect x="137" y="127" width="81" height="31" rx="5" fill="#b89d8f" opacity=".75"/></svg>
 <div className="home-demo-tag home-demo-lost" aria-hidden="true"><span className="home-tag-hole"/><span className="home-tag-brand">SafeReturn</span><HomeIcon name="tag"/><strong>{lost}</strong><DecorativeQr/><span className="home-tag-rule"/></div>
 <div className="home-demo-tag home-demo-ice" aria-hidden="true"><span className="home-tag-hole"/><span className="home-tag-brand">SafeReturn</span><HomeIcon name="medical"/><strong>{ice}</strong><DecorativeQr/><span className="home-tag-rule"/></div>
 <div className="home-scan-note"><span><HomeIcon name="scan"/></span><div><strong>{scan}</strong><small>{share}</small></div><HomeIcon name="check"/></div>
 </div><figcaption>{note}</figcaption></figure>;
}

