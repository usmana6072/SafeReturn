import { changeLanguage } from "./actions";
import { getLanguage, messages } from "../lib/i18n";
import { getCatalog } from "../lib/catalog";
import { FeaturedCatalog } from "../components/catalog";

export default async function Home() {
  const language = await getLanguage();
  const t = messages[language];
  const catalog = await getCatalog(true);
  const links = <><a href="#stickers">{t.products}</a><a href="#how-it-works">{t.how}</a><a href="#faq">{t.help}</a><a href="/login">{language === "ur" ? "لاگ اِن" : "Log in"}</a></>;
  return <>
    <a href="#main" className="skip-link">{t.skip}</a>
    <header className="site-header">
      <div className="container header-inner">
        <a href="/" className="brand" aria-label="SafeReturn"><span className="brand-mark" aria-hidden="true">S</span><bdi>SafeReturn</bdi></a>
        <nav className="desktop-nav" aria-label={t.menu}>{links}</nav>
        <form action={changeLanguage}><input type="hidden" name="language" value={language === "en" ? "ur" : "en"}/><button className="language-button" lang={language === "en" ? "ur" : "en"}>{language === "en" ? "اردو" : "English"}</button></form>
        <details className="mobile-menu"><summary>{t.menu}</summary><nav aria-label={t.menu}>{links}</nav></details>
      </div>
    </header>
    <main id="main" tabIndex={-1}>
      <section className="container hero">
        <div><p className="eyebrow">{t.eyebrow}</p><h1>{t.title}</h1><p className="intro">{t.intro}</p><div className="hero-actions"><a className="button" href="#stickers">{t.primary}</a><a className="button secondary" href="#how-it-works">{t.secondary}</a></div><ul className="chips">{t.chips.map(chip => <li key={chip}>{chip}</li>)}</ul></div>
        <div className="kit-display"><span className="display-label">{t.pair}</span><div className="tag-pair">{[["A", t.lost, t.lostText], ["B", t.ice, t.iceText]].map(([tag, title, text]) => <article className={`tag tag-${tag}`} key={tag}><span className="tag-letter" aria-hidden="true">{tag}</span><span className="tag-brand"><bdi>SafeReturn</bdi></span><span className="purpose-icon" aria-hidden="true">{tag === "A" ? "↗" : "+"}</span><h2>{title}</h2><p>{text}</p></article>)}</div><p className="display-note">{t.profileNote}</p></div>
      </section>
      <section className="catalog-section" id="stickers"><div className="container"><p className="eyebrow">{t.catalogEyebrow}</p><h2>{t.catalogTitle}</h2><FeaturedCatalog catalog={catalog} language={language} /></div></section>
      <section className="container section" id="how-it-works"><p className="eyebrow">{t.how}</p><h2>{t.stepsTitle}</h2><ol className="steps">{t.steps.map(([title, text], index) => <li className="step" key={title}><span className="step-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span><h3>{title}</h3><p>{text}</p></li>)}</ol></section>
      <section className="container privacy-section"><div className="privacy-art" aria-hidden="true">↗<span>+</span></div><div><p className="eyebrow"><bdi>SafeReturn</bdi></p><h2>{t.privacyTitle}</h2><p>{t.privacyText}</p><h3>{t.copiesTitle}</h3><p>{t.copiesText}</p></div></section>
      <section className="container section faq-section" id="faq"><h2>{t.faqTitle}</h2>{t.faqs.map(([question, answer]) => <details key={question}><summary>{question}</summary><p>{answer}</p></details>)}</section>
      <aside className="container safety-note"><p>{t.safety}</p></aside>
    </main>
    <footer className="container footer"><div><bdi className="brand">SafeReturn</bdi><p>{t.footer}</p></div><nav aria-label={t.menu}>{links}</nav><small><bdi>© 2026 SafeReturn</bdi></small></footer>
  </>;
}
