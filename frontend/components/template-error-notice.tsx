"use client";
import { templateError, TemplateApiError } from '../lib/admin-templates-client';

export function TemplateErrorNotice({message,ur=false}:{message:string;ur?:boolean}) {
 if(!message)return null;
 const recent=message===templateError(new TemplateApiError(403,'REAUTH_REQUIRED'),ur);
 return <p role="alert">{message}{recent&&<> <a href="/admin/security/mfa?returnTo=%2Fadmin%2Ftemplates" target="_blank" rel="noopener noreferrer" className="underline">Verify MFA in a new tab</a>. Keep this editor open. After verification, return here, review your input and retry the same action. Nothing retries automatically.</>}</p>;
}
