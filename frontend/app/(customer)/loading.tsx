import {getLanguage} from '../../lib/i18n';
export default async function Loading() {
  return <p role="status" aria-live="polite">{await getLanguage()==='ur'?'آپ کی معلومات لوڈ ہو رہی ہیں…':'Loading your information…'}</p>;
}
