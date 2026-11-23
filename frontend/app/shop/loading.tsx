export default function Loading() {
  return <div className="shop-screen shop-loading" role="status" aria-busy="true"><span className="sr-only">Loading products / مصنوعات لوڈ ہو رہی ہیں</span><i className="shop-loading-title" aria-hidden="true"/><i className="shop-loading-search" aria-hidden="true"/><div className="shop-grid" aria-hidden="true">{[0,1,2].map(i=><div key={i} className="shop-card"><i/><i/><i/></div>)}</div></div>;
}
