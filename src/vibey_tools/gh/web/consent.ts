// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The cookie-consent banner's behaviour (documentation.cookie_consent). TypeScript is the only
// authored form (sub-doctrine 9.f); scripts/typescript_artifacts.py compiles this file to
// `consent.js`, which the release-surfaces workflow inlines after the banner's markup. The
// choice is kept per browser; a reader who has chosen is never asked again, and the choice
// is passed to Google Consent Mode v2 (analytics.ts set the default to denied).
(() => {
  const KEY = "vibey-docs-consent";
  type Choice = "granted" | "denied";
  const page = window as unknown as { gtag?: (...args: unknown[]) => void };
  const grant = (value: Choice): void => {
    if (typeof page.gtag !== "function") {
      return;
    }
    page.gtag("consent", "update", {
      ad_storage: value,
      ad_user_data: value,
      ad_personalization: value,
      analytics_storage: value,
    });
  };
  const bar = document.getElementById("vibey-consent");
  const hide = (): void => {
    if (bar) {
      bar.style.display = "none";
    }
  };
  const choose = (value: Choice): void => {
    try {
      window.localStorage.setItem(KEY, value);
    } catch {
      // Private windows may refuse storage; the choice still holds for this page.
    }
    grant(value);
    hide();
  };
  let stored: string | null = null;
  try {
    stored = window.localStorage.getItem(KEY);
  } catch {
    // No storage: ask again next time, rather than guess.
  }
  if (stored === "granted" || stored === "denied") {
    grant(stored);
    return;
  }
  if (!bar) {
    return;
  }
  bar.style.display = "block";
  document.getElementById("vibey-consent-accept")?.addEventListener("click", () => choose("granted"));
  document.getElementById("vibey-consent-decline")?.addEventListener("click", () => choose("denied"));
})();
