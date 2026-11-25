import { Suspense } from "react";
import { changeLanguage } from "./actions";
import { getLanguage, messages } from "../lib/i18n";
import { HomeIcon, HomeVisual, DecorativeQr } from "../components/home-visual";
import { HomeMenu } from "../components/home-menu";
import { FeaturedProductsSection } from "../components/featured-products-section";
import { ProductsSkeleton } from "../components/products-skeleton";
import "./home.css";

export default async function Home() {
  const language = await getLanguage(),
    t = messages[language],
    h = t.home,
    ur = language === "ur";
  const links = (
    <>
      <a href="#stickers">{t.products}</a>
      <a href="#how-it-works">{t.how}</a>
      <a href="#faq">{t.help}</a>
      <a href="/login">{h.login}</a>
    </>
  );

  return (
    <div className="home-page">
      <a href="#main" className="skip-link">
        {t.skip}
      </a>
      <header className="site-header home-header">
        <div className="home-container header-inner">
          <a className="brand home-brand" href="/" aria-label="SafeReturn">
            <img src="/brand/safereturn_logo.svg" alt="" width="34" height="34" />
            <bdi>SafeReturn</bdi>
          </a>
          <nav className="desktop-nav" aria-label={t.menu}>
            {links}
          </nav>
          <form action={changeLanguage}>
            <input type="hidden" name="language" value={ur ? "en" : "ur"} />
            <button className="language-button" lang={ur ? "en" : "ur"}>
              {ur ? "English" : "اردو"}
            </button>
          </form>
          <HomeMenu label={t.menu}>
            {links}
            <a className="home-menu-shop" href="/shop">
              {h.navShop}
              <HomeIcon name="arrow" />
            </a>
          </HomeMenu>
        </div>
      </header>

      <main id="main" tabIndex={-1}>
        <section className="home-container home-hero">
          <div className="home-hero-copy">
            <p className="home-eyebrow">
              <span />
              {t.eyebrow}
            </p>
            <h1>{t.title}</h1>
            <p className="home-intro">{t.intro}</p>
            <div className="home-actions">
              <a className="home-button home-primary" href="#stickers">
                {t.primary}
                <HomeIcon name="arrow" />
              </a>
              <a className="home-button home-secondary" href="#how-it-works">
                <HomeIcon name="scan" />
                {t.secondary}
              </a>
            </div>
            <ul className="home-trust">
              {[...t.chips.slice(0, 2), h.privacyChip].map((chip) => (
                <li key={chip}>
                  <HomeIcon name="check" />
                  {chip}
                </li>
              ))}
            </ul>
            <p className="home-hero-note">{h.heroNote}</p>
          </div>
          <HomeVisual
            lost={t.lost}
            ice={t.ice}
            label={h.visualLabel}
            scan={h.scanLabel}
            share={h.shareLabel}
            note={h.visualNote}
            illustration={h.illustration}
          />
        </section>

        <section className="home-purpose-section">
          <div className="home-container">
            <div className="home-section-head">
              <div>
                <p className="home-eyebrow">{h.purposeEyebrow}</p>
                <h2>{t.pair}</h2>
              </div>
              <p>{h.purposeIntro}</p>
            </div>
            <div className="home-purpose-grid">
              {[
                { title: t.lost, text: t.lostText, label: h.lostFor, icon: "tag" as const, className: "home-purpose-lost" },
                { title: t.ice, text: t.iceText, label: h.iceFor, icon: "medical" as const, className: "home-purpose-ice" },
              ].map((card) => (
                <article className={"home-purpose-card " + card.className} key={card.icon}>
                  <div className="home-purpose-copy">
                    <span className="home-purpose-icon">
                      <HomeIcon name={card.icon} />
                    </span>
                    <p className="home-card-kicker">{card.label}</p>
                    <h3>{card.title}</h3>
                    <p>{card.text}</p>
                  </div>
                  <div className="home-purpose-art" aria-hidden="true">
                    <HomeIcon name={card.icon} />
                    <DecorativeQr />
                  </div>
                </article>
              ))}
            </div>
            <p className="home-profile-note">
              <HomeIcon name="profile" />
              {t.profileNote}
            </p>
          </div>
        </section>

        <section className="home-collection" id="stickers">
          <div className="home-container">
            <div className="home-section-head">
              <div>
                <p className="home-eyebrow">{t.catalogEyebrow}</p>
                <h2>{t.catalogTitle}</h2>
              </div>
              <p>{h.collectionIntro}</p>
            </div>
            <Suspense fallback={<ProductsSkeleton language={language} />}>
              <FeaturedProductsSection language={language} emptyText={t.catalogEmpty} />
            </Suspense>
          </div>
        </section>

        <section className="home-container home-how" id="how-it-works">
          <div className="home-section-head">
            <div>
              <p className="home-eyebrow">{t.how}</p>
              <h2>{t.stepsTitle}</h2>
            </div>
            <p>{h.howIntro}</p>
          </div>
          <ol className="home-steps">
            {t.steps.map(([title, text], index) => (
              <li key={title}>
                <span className="home-step-number">{String(index + 1).padStart(2, "0")}</span>
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="home-container home-privacy">
          <div className="home-privacy-heading">
            <span className="home-privacy-icon">
              <HomeIcon name="shield" />
            </span>
            <p className="home-eyebrow">{h.privacyEyebrow}</p>
            <h2>{t.privacyTitle}</h2>
            <p>{t.privacyText}</p>
            <a className="home-text-link" href="/account">
              {h.privacyLink}
              <HomeIcon name="arrow" />
            </a>
          </div>
          <div className="home-privacy-features">
            {[
              { title: h.profileFeature, text: h.profileFeatureText, icon: "profile" as const },
              { title: t.copiesTitle, text: t.copiesText, icon: "layers" as const },
              { title: h.sharingFeature, text: h.sharingFeatureText, icon: "shield" as const },
            ].map((item) => (
              <article key={item.icon}>
                <span>
                  <HomeIcon name={item.icon} />
                </span>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.text}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="home-container home-faq" id="faq">
          <div>
            <p className="home-eyebrow">{h.faqEyebrow}</p>
            <h2>{t.faqTitle}</h2>
            <p>{h.faqIntro}</p>
            <a className="home-text-link" href="/help">
              {h.support}
              <HomeIcon name="arrow" />
            </a>
          </div>
          <div className="home-faq-list">
            {t.faqs.map(([question, answer]) => (
              <details key={question}>
                <summary>
                  {question}
                  <span aria-hidden="true" />
                </summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="home-container home-closing">
          <div>
            <p className="home-eyebrow">{h.closingEyebrow}</p>
            <h2>{h.closingTitle}</h2>
            <p>{h.closingText}</p>
          </div>
          <a className="home-button" href="/shop">
            {h.navShop}
            <HomeIcon name="arrow" />
          </a>
        </section>

        <aside className="home-container home-safety">
          <HomeIcon name="shield" />
          <p>{t.safety}</p>
        </aside>
      </main>

      <footer className="home-footer">
        <div className="home-container home-footer-main">
          <div>
            <a className="brand home-brand" href="/">
              <img src="/brand/safereturn_logo.svg" width="32" height="32" alt="" />
              <bdi>SafeReturn</bdi>
            </a>
            <p>{t.footer}</p>
            <small>{h.footerPurpose}</small>
          </div>
          <nav aria-label={h.footerNavigate}>
            <strong>{h.footerNavigate}</strong>
            <a href="#stickers">{t.products}</a>
            <a href="#how-it-works">{t.how}</a>
            <a href="#faq">{t.help}</a>
          </nav>
          <nav aria-label={h.footerAccount}>
            <strong>{h.footerAccount}</strong>
            <a href="/account">{h.account}</a>
            <a href="/shop">{h.navShop}</a>
            <a href="/help">{h.support}</a>
            <a href="/login">{h.login}</a>
          </nav>
        </div>
        <div className="home-container home-footer-bottom">
          <small>
            <bdi>© 2026 SafeReturn</bdi>
          </small>
          <small>English · اردو</small>
        </div>
      </footer>
    </div>
  );
}
