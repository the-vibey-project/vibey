---
id: skill-4-how-the-web-serves-data-84094e0020
purpose: 4 how the web serves data
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-tooling-extraction-and-blocking/SKILL.md
requires: []
links: ["skill-5-the-tool-ladder-4f25f53280"]
---

## §4. How the Web Serves Data

**[DURABLE] Understanding this determines your tool choice (§5) and saves enormous effort.**

### 4.1 The three shapes

| Shape | How to tell | What to use |
|---|---|---|
| **Server-rendered HTML** | Data is in "View Source" | **HTTP client + parser.** Fastest, cheapest |
| **Client-rendered (SPA)** | View Source is a near-empty shell; data appears after JS runs | §4.2 — check for an API first |
| **Hybrid / progressive** | Some in HTML, more loaded on scroll or interaction | Usually §4.2 |

### 4.2 The single most valuable technique in scraping

**[DURABLE] Open DevTools → Network → XHR/Fetch, and reload the page.**

If content loads via JavaScript, **it is almost always coming from an API endpoint
returning JSON** — and calling that endpoint directly is **dramatically faster, more
stable, and less resource-intensive for both parties** than driving a browser. You get
clean structured data instead of parsing markup, and the JSON schema changes far less often
than the CSS does.

**⚠️ This is the technique that most distinguishes people who find scraping easy from
people who find it hard.** Before reaching for a headless browser, always check whether
there's a JSON endpoint behind the page. Also check the **`__NEXT_DATA__`**,
`window.__INITIAL_STATE__`, or equivalent embedded-JSON blobs many frameworks leave in the
HTML — the full dataset is frequently sitting there already serialized.

### 4.3 The structured data sites give you for free

**Sitemaps** (`/sitemap.xml`, often listed in robots.txt) enumerate URLs — **use these
instead of crawling links**. **JSON-LD / schema.org markup** in `<script type="application/
ld+json">` gives you clean product, article, and organization data because sites publish it
for search engines. **OpenGraph and meta tags**, **RSS/Atom feeds**, **microdata**.
**⚠️ Checking for these first regularly turns a two-day scraper into a two-hour one.**

### 4.4 Pagination and state

Offset (`?page=2`), cursor-based (more reliable, and **immune to the shifting-window
problem** where new items push results across page boundaries mid-crawl), infinite scroll
(usually an API call — §4.2), and **POST-based search with hidden state tokens** (the
awkward case, requiring session handling).

---
