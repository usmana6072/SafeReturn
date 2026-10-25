/** Closed metadata contracts. No provider/profile/case payload forwarding. */
export type User = { user_id: string; registered_at: string; email_verified: boolean; provider_access: 'banned' | 'not_banned' };
export type AccountState = { status: 'ready'; state: 'active' | 'suspended'; revision: number; as_of: string; commands_available: boolean } | { status: 'unavailable'; reason_code: 'STATE_UNAVAILABLE' };
export type Detail = { as_of: string; user: User; application_suspension: AccountState };
export type Page = { as_of: string; items: User[]; next_cursor: string | null };
export type Filters = { user_id: string | null; email_verified: boolean | null; provider_access: 'banned' | 'not_banned' | null };
export type Total = { as_of: string; definition: 'retained_nonanonymous_auth_registrations_v1'; filters: Filters; count: { value: number; is_exact: boolean } };
export type Action = 'suspend' | 'restore' | 'recovery';
export type Command = { case_id: string; expected_revision: number; reason_code: string; confirmed: true };
export type Receipt = { user_id: string; case_id: string; action: 'suspend' | 'restore' | 'recovery_escalated'; revision: number; event_id: string; occurred_at: string; state?: 'active' | 'suspended'; fresh_sign_in_required?: true; status?: 'referred' };
export const reasons: Record<Action, string[]> = { suspend: ['suspected_compromise', 'abuse_review', 'security_review'], restore: ['review_cleared'], recovery: ['factor_loss', 'account_access_review'] };
const bad = (): never => { throw new Error('unavailable'); };
function object(value: unknown, fields: string[]): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).sort().join('|') !== [...fields].sort().join('|')) return bad();
  return value as Record<string, unknown>;
}
export function uuid(value: unknown): string {
  if (typeof value !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) return bad();
  return value.toLowerCase();
}
function stamp(value: unknown): string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(value) || !Number.isFinite(Date.parse(value)) || new Date(value).toISOString().slice(0,19) !== value.slice(0,19)) return bad();
  return value;
}
function integer(value: unknown, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < min || value > max) return bad(); return value;
}
function bool(value: unknown): boolean { if (typeof value !== 'boolean') return bad(); return value; }
function user(value: unknown): User {
  const v = object(value, ['user_id','registered_at','email_verified','provider_access']);
  if (v.provider_access !== 'banned' && v.provider_access !== 'not_banned') return bad();
  return { user_id: uuid(v.user_id), registered_at: stamp(v.registered_at), email_verified: bool(v.email_verified), provider_access: v.provider_access };
}
export function parsePage(value: unknown, limit: number): Page {
  const v = object(value, ['as_of','items','next_cursor']);
  if (!Array.isArray(v.items) || v.items.length > limit || (v.next_cursor !== null && (typeof v.next_cursor !== 'string' || !/^[A-Za-z0-9_-]{1,1024}$/.test(v.next_cursor)))) return bad();
  const items = v.items.map(user); if (new Set(items.map(u => u.user_id)).size !== items.length) return bad();
  return { as_of: stamp(v.as_of), items, next_cursor: v.next_cursor as string | null };
}
export function parseDetail(value: unknown, id: string): Detail {
  const v = object(value, ['as_of','user','application_suspension']), u = user(v.user);
  if (u.user_id !== uuid(id)) return bad();
  const state = v.application_suspension as AccountState;
  if (!state || typeof state !== 'object') return bad();
  if (state.status === 'unavailable') {
    const s = object(state,['status','reason_code']); if (s.reason_code !== 'STATE_UNAVAILABLE') return bad();
    return { as_of: stamp(v.as_of), user: u, application_suspension: { status:'unavailable', reason_code:'STATE_UNAVAILABLE' } };
  }
  const s = object(state,['status','state','revision','as_of','commands_available']);
  if (s.status !== 'ready' || (s.state !== 'active' && s.state !== 'suspended')) return bad();
  return { as_of: stamp(v.as_of), user: u, application_suspension: { status:'ready', state:s.state, revision:integer(s.revision,1,2147483647), as_of:stamp(s.as_of), commands_available:bool(s.commands_available) } };
}
export function parseTotal(value: unknown, expected: Filters): Total {
  const v = object(value,['as_of','definition','filters','count']); const f = object(v.filters,['user_id','email_verified','provider_access']), c = object(v.count,['value','is_exact']);
  if (v.definition !== 'retained_nonanonymous_auth_registrations_v1') return bad();
  for (const k of ['user_id','email_verified','provider_access'] as const) if (f[k] !== expected[k]) return bad();
  const n = integer(c.value,0,1000); if (c.is_exact !== (n < 1000)) return bad();
  return { as_of:stamp(v.as_of), definition:v.definition, filters:expected, count:{value:n,is_exact:bool(c.is_exact)} };
}
export function parseCommand(value: unknown, action: Action): Command {
  const v = object(value,['case_id','expected_revision','reason_code','confirmed']);
  if (v.confirmed !== true || typeof v.reason_code !== 'string' || !reasons[action].includes(v.reason_code)) return bad();
  return {case_id:uuid(v.case_id),expected_revision:integer(v.expected_revision,1,2147483646),reason_code:v.reason_code,confirmed:true};
}
export function parseReceipt(value: unknown, action: Action, id: string, command: Command): Receipt {
  const recovery = action === 'recovery';
  const v = object(value,['user_id','case_id','action','revision','event_id','occurred_at',...(recovery ? ['status'] : ['state','fresh_sign_in_required'])]);
  if (uuid(v.user_id) !== uuid(id) || uuid(v.case_id) !== command.case_id || v.action !== (recovery ? 'recovery_escalated' : action) || v.revision !== command.expected_revision + 1) return bad();
  const common = {user_id:uuid(v.user_id),case_id:uuid(v.case_id),action:v.action as Receipt['action'],revision:integer(v.revision,2,2147483647),event_id:uuid(v.event_id),occurred_at:stamp(v.occurred_at)};
  if (recovery) { if (v.status !== 'referred') return bad(); return {...common,status:'referred'}; }
  if (v.state !== (action === 'suspend' ? 'suspended' : 'active') || v.fresh_sign_in_required !== true) return bad();
  return {...common,state:v.state as 'active'|'suspended',fresh_sign_in_required:true};
}
