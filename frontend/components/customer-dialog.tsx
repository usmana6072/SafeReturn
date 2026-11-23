"use client";
import { useEffect, useId, useRef, type ReactNode } from "react";

export function CustomerDialog({ title, ur, busy, onClose, children, dismissOnBackdrop = false }: {title:string;ur:boolean;busy:boolean;onClose:()=>void;children:ReactNode;dismissOnBackdrop?:boolean}) {
  const dialog = useRef<HTMLDialogElement>(null), titleId = useId();
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close(); }, []);
  return <dialog ref={dialog} className="dialog" aria-labelledby={titleId} onCancel={event=>{event.preventDefault();if(!busy)onClose();}}
    onClick={event=>{
      if(!dismissOnBackdrop || busy || event.target!==event.currentTarget)return;
      const bounds=event.currentTarget.getBoundingClientRect();
      if(event.clientX<bounds.left || event.clientX>bounds.right || event.clientY<bounds.top || event.clientY>bounds.bottom)onClose();
    }}>
    <div className="dialoghead"><h2 id={titleId}>{title}</h2><button type="button" disabled={busy} onClick={onClose} aria-label={ur ? "بند کریں" : "Close dialog"}>×</button></div>{children}
  </dialog>;
}
