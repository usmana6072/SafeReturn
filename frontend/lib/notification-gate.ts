import 'server-only';
// No live admission yet; request/browser/environment flags cannot open these.
export function notificationReadAdmitted(): boolean { return false; }
export function notificationRetryAdmitted(): boolean { return false; }
