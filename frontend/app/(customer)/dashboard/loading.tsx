import { getLanguage } from "../../../lib/i18n";

export default async function Loading() {
  const ur = await getLanguage() === "ur";
  return <div className="dashboard dash-loading" role="status" aria-busy="true">
    <span className="sr-only">{ur ? "ڈیش بورڈ لوڈ ہو رہا ہے" : "Loading dashboard"}</span>
    <div aria-hidden="true" className="dash-welcome"><i/><i/><i/></div>
    <div aria-hidden="true" className="dash-metrics">{[0, 1, 2, 3].map(n => <div key={n} className="dash-metric"><i/><i/></div>)}</div>
    <div aria-hidden="true"><i/><div className="dash-actions">{[0, 1, 2, 3].map(n => <i key={n}/>)}</div></div>
    <div aria-hidden="true" className="dash-panels"><div className="dash-panel"><i/><i/></div><div className="dash-panel"><i/><i/></div></div>
  </div>;
}
