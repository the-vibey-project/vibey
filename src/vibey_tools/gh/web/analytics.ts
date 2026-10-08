// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// Google Analytics, started the way Google documents it, with the cookie-consent default
// (documentation.cookie_consent). TypeScript is the only authored form (sub-doctrine 9.f);
// scripts/typescript_artifacts.py compiles this file to `analytics.js`, which the
// release-surfaces workflow inlines into every published page with its two settings as
// attributes on the script tag, so the workflow carries configuration and no JavaScript:
//
//   <script data-ga-id="G-XXXXXXXX" data-consent="true"> ...this file... </script>
//
// With consent on, analytics storage stays denied until the reader accepts (Google Consent
// Mode v2); consent.ts records the choice. The `gtag` function pushes its `arguments` object,
// not an array, because that is what gtag.js reads.
(() => {
  type Gtag = (...args: unknown[]) => void;
  const script = document.currentScript as HTMLScriptElement | null;
  const id = script?.dataset.gaId ?? "";
  if (!id) {
    return;
  }
  const consent = script?.dataset.consent === "true";
  const page = window as unknown as { dataLayer?: unknown[]; gtag?: Gtag };
  const dataLayer: unknown[] = (page.dataLayer = page.dataLayer || []);
  function gtag(..._args: unknown[]): void {
    // eslint-disable-next-line prefer-rest-params -- gtag.js reads an `arguments` object
    dataLayer.push(arguments);
  }
  page.gtag = gtag;
  if (consent) {
    gtag("consent", "default", {
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
      analytics_storage: "denied",
    });
  }
  gtag("js", new Date());
  gtag("config", id);
})();
