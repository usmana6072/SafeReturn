"use client";
import {useFormStatus} from 'react-dom';
import type {ReactNode} from 'react';
export function CustomerSubmit({ur,children,secondary=false}:{ur:boolean;children:ReactNode;secondary?:boolean}) {
  const {pending}=useFormStatus();
  return <button className={secondary?'button secondary':'button'} disabled={pending}>{pending?(ur?'انتظار کریں…':'Please wait…'):children}</button>;
}
