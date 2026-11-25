import { HomeIcon } from "./home-visual";

export function ProductsSkeleton({ language }: { language: "en" | "ur" }) {
  const ur = language === "ur";
  return (
    <div className="products-skeleton-wrap" aria-busy="true" aria-live="polite">
      <div className="catalog-controls">
        <div className="home-carousel-buttons" aria-hidden="true">
          <button type="button" disabled aria-label={ur ? "پچھلی مصنوعات" : "Previous products"}>
            ←
          </button>
          <button type="button" disabled aria-label={ur ? "اگلی مصنوعات" : "Next products"}>
            →
          </button>
        </div>
        <a href="/shop">
          {ur ? "تمام مصنوعات" : "All products"}
          <HomeIcon name="arrow" />
        </a>
      </div>
      <div
        className="featured-scroll"
        tabIndex={0}
        role="region"
        aria-label={ur ? "مصنوعات لوڈ ہو رہی ہیں" : "Loading products"}
      >
        {[1, 2, 3].map((key) => (
          <article className="catalog-card home-product skeleton-product" key={key} aria-hidden="true">
            <div className="home-product-image skeleton-image">
              <div className="skeleton-shimmer" />
            </div>
            <div className="home-product-body skeleton-body">
              <div className="skeleton-line skeleton-badge" />
              <div className="skeleton-line skeleton-title" />
              <div className="skeleton-line skeleton-text" />
              <div className="skeleton-line skeleton-text short" />
              <div className="skeleton-price-row">
                <div className="skeleton-line skeleton-price" />
                <div className="skeleton-line skeleton-unit" />
              </div>
              <div className="skeleton-actions">
                <div className="skeleton-button secondary" />
                <div className="skeleton-button primary" />
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
