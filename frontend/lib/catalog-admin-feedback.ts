/** Fixed local messages only: never render provider bodies or validation inputs. */
const messages: Record<string, [string, string]> = {
  TEMPLATE_VARIANT_MISMATCH: ['The selected template does not match this variant. QR type, exact symbol size and material must match the published design.', 'منتخب ڈیزائن کی QR قسم، سائز اور مواد ویریئنٹ سے ملنا چاہیے۔'],
  TEMPLATE_BINDING_UNAVAILABLE: ['The published design could not be bound. Refresh the template and variant before retrying.', 'منظور شدہ ڈیزائن منسلک نہیں ہو سکا۔ دوبارہ لوڈ کریں۔'],
  TEMPLATE_QR_ORIGIN_REQUIRED: ['The public QR page address is not configured for printing. Configure the hosted portal address; the QR opens the owner-selected public details page.', 'پرنٹ کے لیے عوامی QR صفحے کا پتہ درکار ہے۔'],
  LEGACY_PRODUCT_TYPE: ["Legacy pair products retain their original QR model. Create a new product for an independent QR.", "پرانے جوڑے کی قسم برقرار ہے۔ آزاد QR کے لیے نئی مصنوعہ بنائیں۔"],
  QR_TYPE_TEMPLATE_APPROVAL_REQUIRED: ["Each active size needs a valid template binding for its QR type. Select a published design and save the variant; matching size and material are required.", "ہر سائز کے لیے منتخب QR قسم کا منظور شدہ پرنٹ ڈیزائن درکار ہے۔"],
  QR_TYPE_REQUIRED: ['Select Lost or Emergency for this product.', 'مصنوعہ کے لیے Lost یا ایمرجنسی منتخب کریں۔'],
  DUPLICATE_SIZE: ['Each available size must appear only once.', 'ہر دستیاب سائز صرف ایک بار درج کریں۔'],

  CREATE_AS_DRAFT: ['Create this product as a draft first. Then add its variant and verified image before publishing.', 'پہلے مصنوعہ ڈرافٹ کے طور پر محفوظ کریں، پھر ویریئنٹ اور تصدیق شدہ تصویر شامل کر کے شائع کریں۔'],
  FUTURE_PRODUCT_DISABLED: ['Select an active QR Stickers category (slug: qr-stickers). Other product categories are not enabled.', 'فعال QR Stickers قسم منتخب کریں جس کا سلگ qr-stickers ہو۔ دیگر اقسام ابھی دستیاب نہیں۔'],
  PHYSICAL_CATALOG_APPROVAL_REQUIRED: ['Add an active PKR variant using pdf_label, a QR symbol size of at least 30 mm, and a reviewed template key/version configured as approved. Configured choices do not grant renderer or physical approval.', 'فعال PKR ویریئنٹ میں pdf_label، کم از کم 30 ملی میٹر QR سائز اور منظور شدہ ٹیمپلیٹ کی شناخت و ورژن درکار ہیں۔ ترتیب شدہ انتخاب رینڈرر یا اصل پرنٹ کی منظوری نہیں دیتا۔'],
  VERIFIED_PUBLIC_IMAGE_REQUIRED: ['Attach a public product image and wait for server verification before publishing. Selecting a file alone does not attach it.', 'اشاعت سے پہلے عوامی مصنوعات کی تصویر منسلک کریں اور سرور کی تصدیق مکمل ہونے دیں۔ صرف فائل منتخب کرنا کافی نہیں۔'],
  VERSION_MISMATCH: ['This record changed. Your entries remain below. Reload the list, reopen Edit, and review the latest record before saving again.', 'ریکارڈ تبدیل ہو گیا ہے۔ آپ کا اندراج نیچے موجود ہے۔ فہرست دوبارہ لوڈ کریں، ترمیم کھولیں اور تازہ ریکارڈ دیکھ کر محفوظ کریں۔'],
  CATALOG_CONFLICT: ['A catalog value conflicts with an existing record. Check the slug or SKU, then reload and review before retrying.', 'کیٹلاگ کی قدر موجودہ ریکارڈ سے متصادم ہے۔ سلگ یا SKU چیک کریں، پھر دوبارہ لوڈ کر کے جائزہ لیں۔'],
  IDEMPOTENCY_KEY_REUSED: ['This retry conflicts with an earlier command. Reload and review the saved record before making a new change.', 'یہ کوشش پچھلی کارروائی سے متصادم ہے۔ نئی تبدیلی سے پہلے محفوظ ریکارڈ دوبارہ لوڈ کر کے دیکھیں۔'],
  ARCHIVED_PRODUCT: ['An archived product cannot be republished through this editor. Keep its historical records intact.', 'محفوظ شدہ پرانی مصنوعہ اس ایڈیٹر سے دوبارہ شائع نہیں ہو سکتی۔ اس کی تاریخ برقرار رکھیں۔'],
  PUBLIC_ASSET_FOLDER_REQUIRED: ['Use a public marketing image in the configured catalog folder. Private files cannot be attached.', 'کیٹلاگ کے مقررہ فولڈر میں عوامی مصنوعات کی تصویر استعمال کریں۔ نجی فائل منسلک نہیں کی جا سکتی۔'],
  INVALID_PUBLIC_ASSET: ['The image could not be verified as an approved public raster asset. Check its public ID, format and upload configuration.', 'تصویر کی عوامی منظور شدہ فائل کے طور پر تصدیق نہیں ہوئی۔ شناخت، فارمیٹ اور اپ لوڈ کی ترتیب چیک کریں۔'],
};
export async function catalogFailure(response: Response, ur: boolean): Promise<string> {
  let code: unknown;
  try { const data = await response.json(); code = data?.error?.code; } catch { /* Safe status fallback. */ }
  const index = ur ? 1 : 0;
  // Authentication/authorization status takes precedence over any response body.
  if (response.status === 401) return ur ? 'سیشن ختم ہو گیا۔ دوبارہ لاگ اِن کریں۔ آپ کا اندراج نیچے موجود ہے۔' : 'Your session expired. Sign in again. Your entries remain below.';
  if (response.status === 403) return ur ? 'تصدیق شدہ ای میل، MFA اور مجاز کیٹلاگ کردار درکار ہے۔' : 'Verified email, current MFA and an authorized catalog role are required.';
  if (response.status === 412) return messages.VERSION_MISMATCH[index];
  if (response.status >= 500) return ur ? 'کیٹلاگ سروس دستیاب نہیں۔ آپ کا اندراج برقرار ہے؛ دوبارہ کوشش سے پہلے لوڈ کر کے محفوظ نتیجہ چیک کریں۔' : 'Catalog service unavailable. Your entries remain; this does not confirm that a save failed. Reload and check before retrying.';
  if (typeof code === 'string' && Object.hasOwn(messages, code)) return messages[code][index];
  if (response.status === 404) return ur ? 'ریکارڈ دستیاب نہیں۔ فہرست دوبارہ لوڈ کر کے رسائی چیک کریں۔' : 'Record unavailable. Reload the list and check access.';
  return ur ? 'محفوظ نہیں ہوا۔ سلگ، منفرد SKU، PKR قیمت، سائز اور لازمی فیلڈز چیک کریں۔ آپ کا اندراج برقرار ہے۔' : 'Not saved. Check the slug, unique SKU, PKR price, size and required fields. Your entries remain below.';
}

// Reuse fixed messages in the Products-only client without displaying upstream text.
export function catalogCodeMessage(code: string, ur = false): string | undefined {
  return Object.hasOwn(messages, code) ? messages[code][ur ? 1 : 0] : undefined;
}
