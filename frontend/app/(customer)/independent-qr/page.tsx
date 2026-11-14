import {IndependentQRs} from '../../../components/independent-qr';
import {getLanguage} from '../../../lib/i18n';
export default async function Page(){return <IndependentQRs ur={await getLanguage()==='ur'}/>;}
