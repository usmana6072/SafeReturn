/** Display text only; never infer or merge authoritative states. */
const labels:Record<string,[string,string]>={
 draft:['Draft','مسودہ'],placed:['Placed','درج شدہ'],processing:['Processing','زیرِ عمل'],fulfilled:['Fulfilled','مکمل'],cancelled:['Cancelled','منسوخ'],
 awaiting_transfer:['Awaiting transfer','منتقلی کا انتظار'],proof_submitted:['Proof submitted','ثبوت جمع ہوا'],under_review:['Under review','زیرِ جائزہ'],verified:['Verified','تصدیق شدہ'],rejected:['Rejected','مسترد'],refunded:['Refunded','رقم واپس ہوئی'],
 unallocated:['Unallocated','غیر مختص'],allocated:['Allocated','مختص'],packed:['Packed','پیک شدہ'],dispatched:['Dispatched','روانہ'],delivered:['Delivered','پہنچا دیا گیا'],exception:['Exception','استثنائی حالت'],
 reserved:['Reserved','ریزرو شدہ'],released:['Released','ریزرویشن ختم'],initiated:['Initiated','شروع ہوئی'],submitted:['Submitted','جمع ہوئی'],expired:['Expired','مدت ختم'],disputed:['Disputed','متنازع'],
 requested:['Requested','درخواست موصول'],investigating:['Investigating','تحقیق جاری'],approved:['Approved','منظور'],escalated:['Escalated','مزید جائزے کو بھیجا'],completed:['Completed','مکمل'],
 not_requested:['Not requested','درخواست نہیں ہوئی'],queued:['Queued','قطار میں'],rendering:['Rendering','تیاری جاری'],ready:['Ready','تیار'],downloaded:['Downloaded','حاصل کیا گیا'],qa_passed:['QA passed','جانچ منظور'],failed:['Failed','ناکام'],superseded:['Superseded','نیا ورژن موجود'],deleted:['Deleted','حذف شدہ'],restricted:['Restricted','محدود'],
 newest:['Newest first','نیا پہلے'],oldest:['Oldest first','پرانا پہلے'],
 REVIEW_PENDING:['Payment review pending','ادائیگی کا جائزہ باقی'],
 ATTEMPT_ORDER_AMOUNT_MISMATCH:['Attempt and order amounts differ','کوشش اور آرڈر کی رقم مختلف'],
 ATTEMPT_ORDER_CURRENCY_MISMATCH:['Attempt and order currencies differ','کوشش اور آرڈر کی کرنسی مختلف'],
 VERIFIED_HISTORY_MISMATCH:['Verified history mismatch','تصدیق کی تاریخ میں فرق'],
 ORDER_SETTLEMENT_MISMATCH:['Order and recorded settlement mismatch','آرڈر اور درج وصولی میں فرق'],
 VERIFIED_ALLOCATION_MISMATCH:['Verified payment and allocation mismatch','تصدیق شدہ ادائیگی اور تخصیص میں فرق'],
 DUPLICATE_VERIFIED_REFERENCE:['Duplicate verified reference','تصدیق شدہ حوالہ دہرایا گیا'],
 BANK_LEDGER_AMOUNT_COMPARISON:['Bank ledger amount comparison','بینک کھاتے کی رقم کا موازنہ'],
 REJECTED_REFERENCE_MATCHES:['Rejected reference matches','مسترد حوالوں کا ملاپ'],
};
export function orderLabel(value:string,ur:boolean):string{return labels[value]?.[ur?1:0]??value;}
