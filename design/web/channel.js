(() => {
  "use strict";

  // Theme: Light, Dark or System. System is the default: it follows the operating system and
  // switches live when the OS does. A choice persists per device. The stylesheet does the
  // colouring from `data-theme` on <html>; Bootstrap's own components follow `data-bs-theme`.
  const THEME_KEY = "vibey.theme";
  const THEME_MODES = ["light", "dark", "system"];
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
  const readThemeMode = () => {
    try {
      const stored = window.localStorage.getItem(THEME_KEY);
      return THEME_MODES.includes(stored) ? stored : "system";
    } catch {
      return "system";
    }
  };
  let themeMode = readThemeMode();
  const applyTheme = () => {
    const dark = themeMode === "dark" || (themeMode === "system" && systemDark.matches);
    if (themeMode === "system") {
      delete root.dataset.theme;
    } else {
      root.dataset.theme = themeMode;
    }
    if (dark) {
      document.documentElement.dataset.bsTheme = "dark";
    } else {
      document.documentElement.dataset.bsTheme = "light";
    }
    document.querySelectorAll(".theme-switch button").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.mode === themeMode));
    });
  };
  applyTheme();
  systemDark.addEventListener("change", () => themeMode === "system" && applyTheme());
  const themeIcons = {
    light: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    dark: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
    system: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  };
  const themeNav = document.querySelector("#navbar-collapse .ms-md-auto") || document.querySelector("#navbar-collapse .navbar-nav");
  if (themeNav) {
    const item = document.createElement("li");
    item.className = "nav-item d-flex align-items-center";
    const group = document.createElement("div");
    group.className = "theme-switch";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Colour theme");
    for (const mode of THEME_MODES) {
      const button = document.createElement("button");
      const label = { light: "Light", dark: "Dark", system: "System" }[mode];
      button.type = "button";
      button.dataset.mode = mode;
      button.title = label;
      button.setAttribute("aria-label", `${label} theme`);
      button.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${themeIcons[mode]}</svg>`;
      button.addEventListener("click", () => {
        themeMode = mode;
        try {
          window.localStorage.setItem(THEME_KEY, mode);
        } catch {
          // Private windows may refuse storage; the choice still holds for this page.
        }
        applyTheme();
      });
      group.append(button);
    }
    item.append(group);
    themeNav.prepend(item);
    applyTheme();
  }

  const segments = window.location.pathname.split("/").filter(Boolean);
  const channel = segments.includes("develop") ? "develop" : "main";
  document.body.dataset.releaseChannel = channel;

  const brand = document.querySelector(".navbar-brand");
  if (brand) {
    const badge = document.createElement("span");
    badge.className = "release-badge";
    badge.innerHTML = `<span aria-hidden="true"></span>${channel === "main" ? "__PRODUCTION_LABEL__" : "__PREVIEW_LABEL__"}`;
    brand.insertAdjacentElement("afterend", badge);
  }

  const primaryNav = document.querySelector("#navbar-collapse .navbar-nav");
  if (primaryNav) {
    const pagesRoot = "__PAGES_ROOT__";
    primaryNav.querySelectorAll("a.nav-link").forEach((link) => {
      if (link.textContent.trim() === "Home") {
        link.href = pagesRoot;
      } else {
        link.closest("li")?.remove();
      }
    });
    for (const [label, target] of [["__PRODUCTION_LABEL__", "main"], ["__PREVIEW_LABEL__", "develop"]]) {
      const item = document.createElement("li");
      item.className = "nav-item";
      const link = document.createElement("a");
      link.className = `nav-link channel-link${channel === target ? " active" : ""}`;
      link.href = `${pagesRoot}${target}/`;
      link.textContent = label;
      item.append(link);
      primaryNav.append(item);
    }
    document.querySelectorAll("[data-release-target]").forEach((link) => {
      link.href = `${pagesRoot}${link.dataset.releaseTarget}/`;
    });
  }

  const editLink = [...document.querySelectorAll("a.nav-link")].find((link) =>
    link.textContent.includes("Edit on GitHub"),
  );
  if (editLink) {
    editLink.href = editLink.href.replace("/edit/main/", `/edit/${channel}/`);
  }

  const footer = document.querySelector("footer.col-md-12");
  if (footer) {
    const provenance = document.createElement("p");
    provenance.className = "release-provenance";
    provenance.innerHTML = [
      `<strong>Provenance</strong>`,
      `<a href="__REPOSITORY_URL__/tree/__RELEASE_SHA__">__REPOSITORY__@__SHORT_SHA__</a>`,
      `<span>branch / __RELEASE_BRANCH__</span>`,
      `<span>channel / __RELEASE_CHANNEL__</span>`,
      `<span>Made with ❤️ by <a href="https://the-vibey-project.github.io/vibey/">Vibey</a>, Developed by <a href="https://vibewithadam.matthewsteinberger.com/">Adam Matthew Steinberger</a> (<a href="https://github.com/adammatthewsteinberger/">@adammatthewsteinberger</a>).</span>`,
    ].join('<span aria-hidden="true">·</span>');
    footer.append(provenance);
  }

  // The documentation's own downloadable forms — the research paper and the book — are
  // published beside the pages they mirror: release-surfaces copies paper.pdf, paper/,
  // book.epub, book.pdf and book-print.html into the channel site. Which of them exist on
  // THIS deploy is substituted below from file presence in the built site, never from
  // configuration, so a link is never rendered to something that was not produced. An
  // unsubstituted placeholder (an older workflow) degrades to "nothing to show".
  const surfacesRaw = '__DOC_SURFACES__';
  const surfaces = surfacesRaw.startsWith("{") ? JSON.parse(surfacesRaw) : {};
  const channelRoot = `__PAGES_ROOT__${channel}/`;
  const surfaceLinks = (items) =>
    items
      .filter(([present]) => present)
      .map(([, label, file]) => `<a href="${channelRoot}${file}">${label}</a>`)
      .join(' <span aria-hidden="true">·</span> ');
  const paperLinks = surfaceLinks([
    [surfaces.paper_pdf, "PDF", "paper.pdf"],
    [surfaces.paper_html, "HTML", "paper/"],
  ]);
  // The governance corpus (sub-doctrine 7.b), in the order of authority, linked only for the
  // pages this deploy actually published.
  const governanceNames = {
    constitution: "Constitution",
    doctrines: "Doctrines",
    commandments: "Commandments",
    "bill-of-rights": "Bill of Rights",
  };
  const governanceOrder = ["constitution", "doctrines", "commandments", "bill-of-rights"];
  // Slugs come from repository file names: only plain ones are linked, the URL component is
  // encoded and the label escaped, so a name can never inject markup into a page.
  const publishedGovernance = (Array.isArray(surfaces.governance) ? surfaces.governance : []).filter(
    (slug) => typeof slug === "string" && /^[a-z0-9][a-z0-9-]*$/.test(slug),
  );
  const escapeText = (text) =>
    String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const governancePages = [
    ...governanceOrder.filter((slug) => publishedGovernance.includes(slug)),
    ...publishedGovernance.filter((slug) => !governanceOrder.includes(slug)).sort(),
  ];
  const governanceLinks = governancePages
    .map(
      (slug) =>
        `<a href="${channelRoot}governance/${encodeURIComponent(slug)}/">${escapeText(governanceNames[slug] || slug.replace(/^(sd-\d+).*$/i, "$1").toUpperCase())}</a>`,
    )
    .join(' <span aria-hidden="true">·</span> ');
  const bookLinks = surfaceLinks([
    [surfaces.book_pdf, "PDF", "book.pdf"],
    [surfaces.book_epub, "EPUB", "book.epub"],
    [surfaces.book_print, "print HTML", "book-print.html"],
  ]);

  // One click from every page: a Paper and a Book entry in the primary navigation.
  if (primaryNav) {
    const bookTarget = surfaces.book_pdf
      ? "book.pdf"
      : surfaces.book_epub
        ? "book.epub"
        : "book-print.html";
    for (const [label, present, file] of [
      ["Governance", governancePages.length > 0, `governance/${encodeURIComponent(governancePages[0] || "")}/`],
      ["Paper", Boolean(paperLinks), surfaces.paper_html ? "paper/" : "paper.pdf"],
      ["Book", Boolean(bookLinks), bookTarget],
    ]) {
      if (!present) continue;
      const item = document.createElement("li");
      item.className = "nav-item";
      const link = document.createElement("a");
      link.className = "nav-link surface-link";
      link.href = `${channelRoot}${file}`;
      link.textContent = label;
      item.append(link);
      primaryNav.append(item);
    }
  }

  // And on every page's footer, beside the provenance line, every format that exists.
  if (footer && (paperLinks || bookLinks || governanceLinks)) {
    const reading = document.createElement("p");
    reading.className = "release-surfaces";
    reading.innerHTML = [
      governanceLinks ? `<strong>Governance</strong> ${governanceLinks}` : "",
      paperLinks ? `<strong>Research paper</strong> ${paperLinks}` : "",
      bookLinks ? `<strong>The book</strong> ${bookLinks}` : "",
    ]
      .filter(Boolean)
      .join('<span aria-hidden="true">·</span>');
    footer.append(reading);
  }
})();
