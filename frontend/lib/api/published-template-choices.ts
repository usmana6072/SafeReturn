import { guardedBackendFetch } from './quarantine';
import { templateResult, type TemplatePage, type Detail } from '../admin-templates-contract';
import { parseTemplateChoices, type TemplateChoices } from '../catalog-template-choices';

export class PublishedTemplateError extends Error {
  constructor(public status = 503) { super('Published templates unavailable'); }
}

// Compose only existing authenticated, read-only APIs. Never infer publication
// from a configured key or grant a variant binding/rendering approval here.
export async function publishedTemplateChoices(origin: string, token: string, configured: TemplateChoices, signal: AbortSignal): Promise<TemplateChoices> {
  let requests = 0;
  async function json(response: Response, max: number) {
    if (response.headers.get('content-type')?.split(';')[0].trim() !== 'application/json' || !response.body) throw new PublishedTemplateError();
    const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', { fatal: true });
    let size = 0, value = '';
    try {
      for (;;) {
        const part = await reader.read(); if (part.done) break;
        size += part.value.byteLength; if (size > max) throw new PublishedTemplateError();
        value += decoder.decode(part.value, { stream: true });
      }
      value += decoder.decode(); return JSON.parse(value);
    } finally { await reader.cancel(); }
  }
  async function read(path: string, action: 'list' | 'detail', query: Record<string, string>) {
    if (++requests > 128) throw new PublishedTemplateError();
    const response = await guardedBackendFetch(origin + '/api/v1' + path + '?' + new URLSearchParams(query), {
      method: 'GET', cache: 'no-store', redirect: 'error', signal,
      headers: { Authorization: 'Bearer ' + token, Accept: 'application/json' },
    });
    if (!response.ok) {
      // Legacy configured choices still work when template management is
      // explicitly disabled. Provider/auth failures must not become empty lists.
      if (action === 'list' && requests === 1 && response.status === 503) {
        const error = await json(response, 8192);
        if (error?.error?.code === 'TEMPLATE_MANAGEMENT_DISABLED') return null;
      }
      throw new PublishedTemplateError([401, 403].includes(response.status) ? response.status : 503);
    }
    return templateResult(action, await json(response, 2 * 1024 * 1024));
  }
  const pairs = new Map(configured.items.map(item => [item.template_key + '@' + item.template_version, item]));
  let cursor: string | null = null;
  const cursors = new Set<string>();
  do {
    if (cursor) { if (cursors.has(cursor)) throw new PublishedTemplateError(); cursors.add(cursor); }
    const page = await read('/admin/print-templates', 'list', { status: 'active', limit: '50', ...(cursor ? { cursor } : {}) }) as TemplatePage | null;
    if (!page) return configured;
    for (const template of page.items) {
      if (template.lifecycle_status !== 'active') continue;
      let revisionCursor: string | null = null;
      const revisionCursors = new Set<string>();
      do {
        if (revisionCursor) { if (revisionCursors.has(revisionCursor)) throw new PublishedTemplateError(); revisionCursors.add(revisionCursor); }
        const detail = await read('/admin/print-templates/' + template.template_id, 'detail', { revisions_limit: '50', ...(revisionCursor ? { revisions_cursor: revisionCursor } : {}) }) as Detail;
        if (detail.template.template_id !== template.template_id) throw new PublishedTemplateError();
        if (detail.template.lifecycle_status === 'active') for (const revision of detail.revisions) {
          if (revision.status === 'published' && revision.published_at) {
            const item = { template_key: detail.template.key, template_version: revision.version };
            pairs.set(item.template_key + '@' + item.template_version, item);
            if (pairs.size > 100) throw new PublishedTemplateError();
          }
        }
        revisionCursor = detail.next_cursor;
      } while (revisionCursor);
    }
    cursor = page.next_cursor;
  } while (cursor);
  return parseTemplateChoices({ as_of: new Date().toISOString(), items: [...pairs.values()].sort((a,b) => a.template_key < b.template_key ? -1 : a.template_key > b.template_key ? 1 : a.template_version - b.template_version) });
}
