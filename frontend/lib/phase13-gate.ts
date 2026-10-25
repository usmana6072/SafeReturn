import 'server-only';
// Source-unsafe summary is rejected even if an admission flag is changed.
export function dashboardSummaryAdmitted():boolean{return false;}
export function dashboardTrendsAdmitted():boolean{return false;}
export function auditEventsAdmitted():boolean{return false;}
// This gate covers this panel only, not the existing authentication bootstrap.
export function currentStaffSecurityAdmitted():boolean{return false;}
export function backendLivenessAdmitted():boolean{return false;}
