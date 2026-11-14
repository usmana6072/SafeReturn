"use client";
import { useEffect, useId, useRef, type ReactNode } from "react";

export function CustomerDialog({ title, ur, busy, onClose, children }: {title:string;ur:boolean;busy:boolean;onClose:()=>void;children:ReactNode}) {
  const dialog = useRef<HTMLDialogElement>(null), titleId = useId();
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close(); }, []);
  return <dialog ref={dialog} className="dialog" aria-labelledby={titleId} onCancel={event=>{event.preventDefault();if(!busy)onClose();}}>
    <div className="dialoghead"><h2 id={titleId}>{title}</h2><button type="button" disabled={busy} onClick={onClose} aria-label={ur ? "بند کریں" : "Close dialog"}>×</button></div>{children}
  </dialog>;
}
