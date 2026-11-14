import 'server-only';
// Independent acceptance decisions. Browser/query/environment flags cannot open them.
export function financeSyncReadAdmitted():boolean{return false;}
export function financeSyncRetryAdmitted():boolean{return false;}
export function storageReadAdmitted():boolean{return false;}
// These generic mutations are also ineligible; the relay always rejects them.
export function retentionHoldCreateAdmitted():boolean{return false;}
export function retentionHoldReleaseAdmitted():boolean{return false;}
export function cleanupRetryAdmitted():boolean{return false;}
