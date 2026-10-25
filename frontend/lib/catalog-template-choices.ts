export type TemplateChoice = { template_key: string; template_version: number };
export type TemplateChoices = { as_of: string; items: TemplateChoice[] };
export const templatePath = '/admin/catalog/approved-templates';
export const choiceId = (c: TemplateChoice) => `${c.template_key}@${c.template_version}`;
export function parseTemplateChoices(value: unknown): TemplateChoices {
  if (!value || typeof value !== 'object') throw new Error('unavailable');
  const data = value as TemplateChoices;
  if (Object.keys(data).sort().join(',') !== 'as_of,items' || typeof data.as_of !== 'string'
    || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/.test(data.as_of) || !Number.isFinite(Date.parse(data.as_of))
    || new Date(data.as_of).toISOString().slice(0,19) !== data.as_of.slice(0,19)
    || !Array.isArray(data.items) || data.items.length > 100) throw new Error('unavailable');
  const items: TemplateChoice[] = [];
  for (const item of data.items) {
    if (!item || typeof item !== 'object' || Object.keys(item).sort().join(',') !== 'template_key,template_version'
      || typeof item.template_key !== 'string' || !/^[A-Za-z0-9._-]{3,80}$/.test(item.template_key)
      || !Number.isInteger(item.template_version) || item.template_version < 1 || item.template_version > 100000) throw new Error('unavailable');
    const previous = items.at(-1);
    if (previous && (previous.template_key > item.template_key || previous.template_key === item.template_key && previous.template_version >= item.template_version)) throw new Error('unavailable');
    items.push({ template_key: item.template_key, template_version: item.template_version });
  }
  return { as_of: data.as_of, items };
}
