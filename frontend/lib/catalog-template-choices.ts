export type TemplateChoice = { template_key: string; template_version: number; name?: string; width_mm?: string; height_mm?: string; symbol_mm?: string; english_caption?: boolean; urdu_caption?: boolean };
export type TemplateChoices = { as_of: string; items: TemplateChoice[] };
export const templatePath = '/admin/catalog/approved-templates';
export const choiceId = (c: TemplateChoice) => `${c.template_key}@${c.template_version}`;
function validMm(v: unknown): v is string { return typeof v === 'string' && /^\d{1,3}\.\d{2}$/.test(v) && Number(v) > 0; }
export function parseTemplateChoices(value: unknown): TemplateChoices {
  if (!value || typeof value !== 'object') throw new Error('unavailable');
  const data = value as TemplateChoices;
  if (Object.keys(data).sort().join(',') !== 'as_of,items' || typeof data.as_of !== 'string'
    || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/.test(data.as_of) || !Number.isFinite(Date.parse(data.as_of))
    || new Date(data.as_of).toISOString().slice(0,19) !== data.as_of.slice(0,19)
    || !Array.isArray(data.items) || data.items.length > 100) throw new Error('unavailable');
  const items: TemplateChoice[] = [];
  for (const item of data.items) {
    if (!item || typeof item !== 'object' || !['template_key,template_version','english_caption,height_mm,name,symbol_mm,template_key,template_version,urdu_caption,width_mm'].includes(Object.keys(item).sort().join(','))
      || typeof item.template_key !== 'string' || !/^[A-Za-z0-9._-]{3,80}$/.test(item.template_key)
      || !Number.isInteger(item.template_version) || item.template_version < 1 || item.template_version > 100000) throw new Error('unavailable');
    if (Object.hasOwn(item, 'name') && (typeof item.name !== 'string' || !item.name.trim() || item.name.length > 100
      || !validMm(item.width_mm) || !validMm(item.height_mm) || !validMm(item.symbol_mm)
      || Number(item.width_mm) < 25 || Number(item.width_mm) > 190 || Number(item.height_mm) < 20 || Number(item.height_mm) > 270 || Number(item.symbol_mm) < 15 || Number(item.symbol_mm) > 100
      || typeof item.english_caption !== 'boolean' || typeof item.urdu_caption !== 'boolean')) throw new Error('unavailable');
    const previous = items.at(-1);
    if (previous && (previous.template_key > item.template_key || previous.template_key === item.template_key && previous.template_version >= item.template_version)) throw new Error('unavailable');
    items.push({ template_key: item.template_key, template_version: item.template_version, ...(Object.hasOwn(item, 'name') ? {
      name: item.name, width_mm: item.width_mm, height_mm: item.height_mm, symbol_mm: item.symbol_mm,
      english_caption: item.english_caption, urdu_caption: item.urdu_caption,
    } : {}) });
  }
  return { as_of: data.as_of, items };
}
