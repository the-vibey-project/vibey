// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The ledger explorer: a read-only, block-explorer-style view into a published ledger.
//
// It reads exactly what `vibey ledger site` writes (manifest.json, index.json and
// records/<event_id>.json, format vibey-ledger-site/v1) and nothing else: no server, no
// database, no account, and nothing a visitor searches for leaves their browser.
// TypeScript is the only authored form (sub-doctrine 9.f); scripts/typescript_artifacts.py
// compiles this file to docs/javascripts/explorer.js.
//
// Four rules, each load-bearing:
//   1. Ledger text is data. Every value reaches the page through textContent, never
//      innerHTML, so a payload that says <script> is shown as the words it is.
//   2. Nothing is claimed that was not observed. "Digest matches" is the browser hashing the
//      record it just fetched; when it cannot hash, or the hash differs, the page says so.
//   3. What was left out is shown beside what was kept, on the first screen (7.a).
//   4. It meets the Beauty Bar (docs/design/beauty-bar.md): tokens only, WCAG AA, every
//      control reachable by keyboard, motion that explains and stops when asked, and a
//      designed loading, empty and error state (BB-1, BB-3, BB-5, BB-6).
(() => {
  // ---- the published format: src/vibey/application/ledger_publication.py -----------------
  interface ProjectEntry {
    id: string;
    label?: string;
    sample?: boolean;
  }
  interface ProjectListing {
    projects?: ProjectEntry[];
  }
  interface TrimCounts {
    fields: number;
    paths: number;
    emails: number;
    credentials: number;
  }
  interface Manifest {
    format: string;
    project: { project_id: string; name: string };
    holds: string;
    tier: string;
    seq_range: { first: number | null; last: number | null; events: number };
    published: { records: number; first_seq: number | null; last_seq: number | null };
    chain: { scheme: string; head: string; head_seq: number | null; verified: boolean; findings: number };
    policy: { scheme: string; fingerprint: string };
    withheld: TrimCounts & { events: number; by_reason: Record<string, number> };
    statement: string;
  }
  interface IndexEntry {
    id: string;
    seq: number;
    kind: string;
    phase: string;
    actor: string;
    time: string;
    digest: string;
    tokens: string[];
  }
  interface SiteIndex {
    records: IndexEntry[];
  }
  interface RecordFields {
    event_id: string;
    cycle: number;
    phase: string;
    seq: number;
    kind: string;
    engine_id: string | null;
    causation_id: string | null;
    correlation_id: string;
    provenance: string;
    produced_at: string;
    payload: unknown;
    digest: string;
  }
  interface Neighbour {
    event_id: string;
    seq: number;
  }
  interface RecordDocument {
    record: RecordFields;
    withheld: TrimCounts;
    previous: Neighbour | null;
    next: Neighbour | null;
  }
  interface Ledger {
    base: string;
    manifest: Manifest;
    records: IndexEntry[]; // newest first
  }
  interface View {
    project: string;
    record: string | null;
    q: string;
    kind: string;
    phase: string;
    page: number;
    oldest: boolean;
  }

  // ---- a tiny DOM builder: strings become text nodes, and there is no way to pass HTML --
  type Child = Node | string | number | false | null | undefined | readonly Child[];
  type Attribute = string | number | boolean | null | undefined | EventListener;

  const el = <K extends keyof HTMLElementTagNameMap>(
    tag: K,
    attrs: Readonly<Record<string, Attribute>> | null,
    ...children: Child[]
  ): HTMLElementTagNameMap[K] => {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs ?? {})) {
      if (value === null || value === undefined || value === false) {
        continue;
      }
      if (typeof value === "function") {
        node.addEventListener(key.slice(2), value);
      } else if (key === "class") {
        node.className = String(value);
      } else {
        node.setAttribute(key, value === true ? "" : String(value));
      }
    }
    const append = (child: Child): void => {
      if (child === null || child === undefined || child === false) {
        return;
      }
      if (Array.isArray(child)) {
        child.forEach(append);
      } else if (child instanceof Node) {
        node.append(child);
      } else {
        node.append(document.createTextNode(String(child)));
      }
    };
    children.forEach(append);
    return node;
  };

  // ---- icons: fixed paths from this file, never from the ledger -------------------------
  const SVG = "http://www.w3.org/2000/svg";
  const ICONS: Readonly<Record<string, string>> = {
    search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-4.3-4.3",
    decision: "M12 3v18M5 7h14M5 7l-2 6a3 3 0 0 0 6 0L7 7M19 7l-2 6a3 3 0 0 0 6 0l-2-6",
    phase: "M4 12h14M13 6l6 6-6 6",
    question: "M9.1 9a3 3 0 1 1 4.4 2.6c-.9.5-1.5 1.1-1.5 2.1M12 17.5v.01M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z",
    answer: "M4 5h16v11H9l-5 4V5z",
    idea: "M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z",
    alert: "M12 4 2.5 20h19L12 4zM12 10v4.5M12 17.5v.01",
    check: "M4 12.5 9.5 18 20 6.5",
    flag: "M5 21V4M5 4h11l-2 4 2 4H5",
    box: "M3 7.5 12 3l9 4.5v9L12 21l-9-4.5v-9zM3 7.5 12 12l9-4.5M12 12v9",
    dot: "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    copy: "M9 9h11v11H9zM5 15V4h11",
    arrowLeft: "M19 12H5M11 6l-6 6 6 6",
    arrowRight: "M5 12h14M13 6l6 6-6 6",
    shield: "M12 3 4 6v6c0 4.5 3.2 8 8 9 4.8-1 8-4.5 8-9V6l-8-3zM8.5 12l2.5 2.5L15.5 9.5",
    eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    lock: "M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 0 1 7 0v3",
    clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2",
    users: "M16 19v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 17.5V19M10 4.5a3.2 3.2 0 1 0 0 6.4 3.2 3.2 0 0 0 0-6.4zM20 19v-1.5a3.5 3.5 0 0 0-2.6-3.4",
    refresh: "M20 5v5h-5M4 19v-5h5M18.4 10A7 7 0 0 0 6 7.6L4 10M5.6 14A7 7 0 0 0 18 16.4L20 14",
  };
  const icon = (name: string): SVGSVGElement => {
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "lx-icon");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    const path = document.createElementNS(SVG, "path");
    path.setAttribute("d", ICONS[name] ?? ICONS["dot"] ?? "");
    svg.append(path);
    return svg;
  };

  // ---- what each kind of record is called, drawn as and described as --------------------
  interface KindStyle {
    label: string;
    tone: string;
    icon: string;
  }
  const KINDS: Readonly<Record<string, KindStyle>> = {
    DecisionRecorded: { label: "Decision", tone: "accent", icon: "decision" },
    PhaseTransitioned: { label: "Phase change", tone: "info", icon: "phase" },
    QuestionAsked: { label: "Question", tone: "info", icon: "question" },
    AnswerGiven: { label: "Answer", tone: "info", icon: "answer" },
    AssumptionStated: { label: "Assumption", tone: "neutral", icon: "idea" },
    FindingRaised: { label: "Finding", tone: "warning", icon: "alert" },
    FindingResolved: { label: "Finding resolved", tone: "success", icon: "check" },
    VerdictRendered: { label: "Verdict", tone: "success", icon: "flag" },
    ArtifactProduced: { label: "Artifact", tone: "accent", icon: "box" },
  };
  const kindStyle = (kind: string): KindStyle =>
    KINDS[kind] ?? { label: kind.replace(/([a-z])([A-Z])/g, "$1 $2"), tone: "neutral", icon: "dot" };

  const REASONS: Readonly<Record<string, { label: string; why: string; tone: string }>> = {
    engine_chatter: { label: "Engine chatter", why: "Prompts, model output and tool calls. Never published.", tone: "muted" },
    kind_not_allowlisted: { label: "Not on the allowlist", why: "Spend, gates, failures and other kinds the policy does not name.", tone: "warning" },
    untrusted_provenance: { label: "Text from outside", why: "Web pages and issue bodies vibey did not write.", tone: "danger" },
  };

  const SITE_FORMAT = "vibey-ledger-site/v1";
  const PAGE_SIZE = 20;
  const SHORT = 8;

  // ---- small, pure formatters ----------------------------------------------------------
  const number = (n: number): string => n.toLocaleString("en-US");
  const plural = (n: number, one: string, many: string): string => `${number(n)} ${n === 1 ? one : many}`;
  const short = (text: string | undefined): string => (text && text.length > SHORT * 2 + 1 ? `${text.slice(0, SHORT)}…${text.slice(-SHORT)}` : text || "—");
  const utc = (iso: string): string => iso.replace("T", " ").replace(/:\d\d(\.\d+)?\+00:00$/, " UTC");
  const asText = (value: unknown): string | undefined => (typeof value === "string" && value.trim() ? value.trim() : undefined);
  const clip = (text: string, max: number): string => (text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text);

  const relative = (iso: string): string => {
    const seconds = (new Date(iso).getTime() - Date.now()) / 1000;
    const units: ReadonlyArray<readonly [Intl.RelativeTimeFormatUnit, number]> = [
      ["year", 31536000],
      ["month", 2592000],
      ["week", 604800],
      ["day", 86400],
      ["hour", 3600],
      ["minute", 60],
    ];
    const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
    for (const [unit, size] of units) {
      if (Math.abs(seconds) >= size) {
        return formatter.format(Math.round(seconds / size), unit);
      }
    }
    return "just now";
  };

  const span = (firstIso: string, lastIso: string): string => {
    const minutes = Math.max(0, (new Date(lastIso).getTime() - new Date(firstIso).getTime()) / 60000);
    if (minutes < 90) {
      return `${Math.max(1, Math.round(minutes))} minutes`;
    }
    if (minutes < 60 * 48) {
      return `${Math.round(minutes / 60)} hours`;
    }
    return `${Math.round(minutes / 1440)} days`;
  };

  // One plain sentence for a record, from the fields its kind publishes. Everything returned
  // is text for textContent: nothing here is, or becomes, markup.
  const summarise = (kind: string, payload: unknown): string => {
    const p = (payload ?? {}) as Record<string, unknown>;
    const pick = (...keys: string[]): string | undefined => keys.map((key) => asText(p[key])).find((v) => v !== undefined);
    switch (kind) {
      case "DecisionRecorded": {
        const what = pick("title", "decision");
        const choice = asText(p["choice"]);
        return what && choice && what !== choice ? `${what}: ${choice}` : (what ?? choice ?? "A decision was recorded");
      }
      case "PhaseTransitioned":
        return `${asText(p["from"]) ?? "?"} → ${asText(p["to"]) ?? "?"}${asText(p["guard"]) ? ` (${asText(p["guard"])})` : ""}`;
      case "QuestionAsked":
        return pick("text") ?? "A question was asked";
      case "AnswerGiven":
        return pick("answer") ?? "An answer was given";
      case "AssumptionStated":
        return pick("text") ?? "An assumption was stated";
      case "FindingRaised":
        return `${asText(p["severity"]) ? `${asText(p["severity"])}: ` : ""}${pick("text") ?? "A finding was raised"}`;
      case "FindingResolved":
        return pick("resolution") ?? "A finding was resolved";
      case "ArtifactProduced":
        return `${pick("title", "artifact_id") ?? "An artifact"}${asText(p["artifact_type"]) ? ` (${asText(p["artifact_type"])})` : ""}`;
      case "VerdictRendered":
        return p["complete"] === true ? (p["success"] === true ? "Complete, and it succeeded" : "Complete, but not successful") : "Not complete yet";
      default:
        return pick("choice", "text", "title") ?? "";
    }
  };

  // The same bytes `vibey.domain.ledger.canonical_bytes` hashes: sorted keys, no spaces, and
  // ASCII only (Python's default), so a non-ASCII character is the same \uXXXX escape here.
  const canonical = (value: unknown): string => {
    if (value === null) {
      return "null";
    }
    if (Array.isArray(value)) {
      return `[${value.map(canonical).join(",")}]`;
    }
    if (typeof value === "object") {
      const table = value as Record<string, unknown>;
      return `{${Object.keys(table)
        .sort()
        .map((key) => `${canonical(key)}:${canonical(table[key])}`)
        .join(",")}}`;
    }
    if (typeof value === "string") {
      return JSON.stringify(value).replace(/[\u0080-￿]/g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`);
    }
    return JSON.stringify(value);
  };
  const sha256 = async (text: string): Promise<string> => {
    const digest = await window.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
  };

  // ---- reading the published files, once each ---------------------------------------------
  class LedgerStore {
    private readonly ledgers = new Map<string, Promise<Ledger>>();
    private readonly documents = new Map<string, Promise<RecordDocument>>();

    constructor(private readonly base: string) {}

    async projects(): Promise<ProjectEntry[]> {
      return (await this.json<ProjectListing>(`${this.base}projects.json`)).projects ?? [];
    }

    ledger(id: string): Promise<Ledger> {
      let known = this.ledgers.get(id);
      if (!known) {
        known = this.load(id);
        this.ledgers.set(id, known);
        known.catch(() => this.ledgers.delete(id));
      }
      return known;
    }

    document(ledger: Ledger, id: string): Promise<RecordDocument> {
      const key = `${ledger.base}${id}`;
      let known = this.documents.get(key);
      if (!known) {
        known = this.json<RecordDocument>(`${ledger.base}records/${encodeURIComponent(id)}.json`);
        this.documents.set(key, known);
        known.catch(() => this.documents.delete(key));
      }
      return known;
    }

    private async load(id: string): Promise<Ledger> {
      const base = `${this.base}${id}/`;
      const [manifest, index] = await Promise.all([this.json<Manifest>(`${base}manifest.json`), this.json<SiteIndex>(`${base}index.json`)]);
      if (manifest.format !== SITE_FORMAT) {
        throw new Error(`${id} is ${manifest.format}; this explorer reads ${SITE_FORMAT}`);
      }
      return { base, manifest, records: [...index.records].sort((a, b) => b.seq - a.seq) };
    }

    private async json<T>(url: string): Promise<T> {
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      if (!response.ok) {
        throw new Error(`${url} answered ${response.status}`);
      }
      return (await response.json()) as T;
    }
  }

  // ---- the app --------------------------------------------------------------------------
  class LedgerExplorer {
    private projects: ProjectEntry[] = [];
    private lastList = "";
    private current: { ledger: Ledger; view: View } | null = null;
    private readonly toast = el("div", { class: "lx-toast", role: "status", "aria-live": "polite" });
    private toastTimer = 0;

    constructor(
      private readonly root: HTMLElement,
      private readonly store: LedgerStore,
      private readonly guide: string,
    ) {
      window.addEventListener("hashchange", () => void this.route());
      document.addEventListener("keydown", (event) => this.keys(event));
    }

    async start(): Promise<void> {
      this.root.classList.add("lx");
      this.root.replaceChildren(this.skeleton());
      try {
        this.projects = await this.store.projects();
      } catch (error) {
        this.problem("The list of published ledgers could not be read.", error);
        return;
      }
      if (this.projects.length === 0) {
        this.root.replaceChildren(this.empty("No ledger is published here yet", "When a project publishes its ledger it appears on this page, ready to search.", this.guide, "How a project publishes one"));
        return;
      }
      await this.route();
    }

    // ---- routing: #/<project>[/<event id>][?q=&kind=&phase=&page=&order=] ------------------
    private parse(): View {
      const [path = "", query = ""] = window.location.hash.replace(/^#\/?/, "").split("?");
      const [project, record] = path.split("/").filter(Boolean);
      const params = new URLSearchParams(query);
      return {
        project: project ?? this.projects[0]?.id ?? "",
        record: record ?? null,
        q: (params.get("q") ?? "").trim(),
        kind: params.get("kind") ?? "",
        phase: params.get("phase") ?? "",
        page: Math.max(1, Number.parseInt(params.get("page") ?? "1", 10) || 1),
        oldest: params.get("order") === "oldest",
      };
    }

    private href(change: Partial<View> & { project: string }, base?: View): string {
      const view: View = { record: null, q: "", kind: "", phase: "", page: 1, oldest: false, ...(base ?? {}), ...change };
      const params = new URLSearchParams();
      if (view.q) params.set("q", view.q);
      if (view.kind) params.set("kind", view.kind);
      if (view.phase) params.set("phase", view.phase);
      if (view.oldest) params.set("order", "oldest");
      if (view.page > 1) params.set("page", String(view.page));
      const query = params.toString();
      return `#/${view.project}${view.record ? `/${view.record}` : ""}${query ? `?${query}` : ""}`;
    }

    private go(change: Partial<View> & { project: string }, base?: View): void {
      window.location.hash = this.href(change, base);
    }

    private async route(): Promise<void> {
      const view = this.parse();
      const entry = this.projects.find((p) => p.id === view.project);
      if (!entry) {
        this.problem(`There is no published ledger called “${view.project}”.`, "Choose one of the ledgers listed on this page.", this.href({ project: this.projects[0]?.id ?? "" }));
        return;
      }
      let ledger: Ledger;
      try {
        this.root.setAttribute("aria-busy", "true");
        ledger = await this.store.ledger(view.project);
      } catch (error) {
        this.problem("That ledger could not be read.", error);
        return;
      } finally {
        this.root.removeAttribute("aria-busy");
      }
      this.current = { ledger, view };
      const body = view.record ? await this.recordView(entry, ledger, view) : this.listView(entry, ledger, view);
      if (!view.record) {
        this.lastList = this.href({ ...view, record: null });
      }
      this.root.replaceChildren(body, this.toast);
      this.arrive(view.record ? "record" : "list");
    }

    // After a route change: a screen reader hears the new heading, a sighted person sees the top.
    private arrive(kind: "record" | "list"): void {
      const heading = this.root.querySelector<HTMLElement>("[data-lx-heading]");
      heading?.setAttribute("tabindex", "-1");
      if (kind === "record") {
        this.root.scrollIntoView({ block: "start" });
        heading?.focus({ preventScroll: true });
      }
    }

    // ---- keyboard: / searches, ← → walk the ledger, Esc backs out ---------------------------
    private keys(event: KeyboardEvent): void {
      const target = event.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable);
      if (event.metaKey || event.ctrlKey || event.altKey || !this.current) {
        return;
      }
      if (event.key === "/" && !typing) {
        const box = this.root.querySelector<HTMLInputElement>(".lx-search input");
        if (box) {
          event.preventDefault();
          box.focus();
          box.select();
        }
        return;
      }
      if (event.key === "Escape") {
        if (typing) {
          target.blur();
        } else if (this.current.view.record && this.lastList) {
          window.location.hash = this.lastList;
        }
        return;
      }
      const { view } = this.current;
      if (!typing && view.record && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
        const at = this.current.ledger.records.findIndex((r) => r.id === view.record);
        const next = this.current.ledger.records[event.key === "ArrowLeft" ? at + 1 : at - 1];
        if (next) {
          this.go({ project: view.project, record: next.id }, view);
        }
      }
    }

    // ---- shared pieces ------------------------------------------------------------------
    private badge(kind: string): HTMLElement {
      const style = kindStyle(kind);
      return el("span", { class: `lx-badge lx-tone-${style.tone}` }, icon(style.icon), style.label);
    }

    private copyButton(text: string, what: string): HTMLButtonElement {
      return el(
        "button",
        {
          type: "button",
          class: "lx-copy",
          "aria-label": `Copy the ${what}`,
          title: `Copy the ${what}`,
          onclick: () => void this.copy(text, what),
        },
        icon("copy"),
      );
    }

    private async copy(text: string, what: string): Promise<void> {
      let said = `Copied the ${what}`;
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        said = `Your browser would not let this page copy the ${what}; select it and copy by hand`;
      }
      this.toast.textContent = said;
      this.toast.classList.add("lx-toast-on");
      window.clearTimeout(this.toastTimer);
      this.toastTimer = window.setTimeout(() => this.toast.classList.remove("lx-toast-on"), 2200);
    }

    // The three designed states every screen has (BB-6): loading, empty, error.
    private skeleton(): HTMLElement {
      const bar = (extra: string): HTMLElement => el("div", { class: `lx-skel ${extra}` });
      return el("div", { class: "lx-loading", role: "status", "aria-label": "Loading the ledger" }, bar("lx-skel-hero"), el("div", { class: "lx-skel-row" }, bar("lx-skel-card"), bar("lx-skel-card"), bar("lx-skel-card"), bar("lx-skel-card")), bar("lx-skel-table"));
    }

    private empty(title: string, text: string, href?: string, action?: string): HTMLElement {
      return el("div", { class: "lx-state" }, icon("search"), el("h2", { "data-lx-heading": true }, title), el("p", {}, text), href && action ? el("a", { class: "lx-button", href }, action) : null);
    }

    private problem(title: string, error: unknown, href?: string): void {
      const detail = error instanceof Error ? error.message : String(error);
      this.root.replaceChildren(
        el(
          "div",
          { class: "lx-state lx-state-error", role: "alert" },
          icon("alert"),
          el("h2", { "data-lx-heading": true }, title),
          el("p", {}, "Nothing is wrong with your ledger; this page could not fetch a file it needs. Try again, and if it keeps happening the site may be mid-update."),
          el("p", { class: "lx-detail" }, detail),
          el(
            "div",
            { class: "lx-actions" },
            el("button", { type: "button", class: "lx-button", onclick: () => void this.start() }, icon("refresh"), "Try again"),
            href ? el("a", { class: "lx-button lx-button-quiet", href }, "Back to the start") : null,
          ),
        ),
      );
    }

    // ---- the list view: hero, honesty bar, phase strip, filters, rows -----------------------
    private listView(entry: ProjectEntry, ledger: Ledger, view: View): HTMLElement {
      const { manifest } = ledger;
      return el(
        "div",
        { class: "lx-page" },
        this.hero(entry, ledger, view),
        this.honesty(manifest),
        this.tiles(ledger),
        this.records(entry, ledger, view),
        this.footnote(manifest),
      );
    }

    private hero(entry: ProjectEntry, ledger: Ledger, view: View): HTMLElement {
      const { manifest } = ledger;
      const input = el("input", {
        id: "lx-q",
        type: "search",
        value: view.q,
        placeholder: "Search this ledger: a word, #12, an event id or a digest",
        autocomplete: "off",
        spellcheck: "false",
        enterkeyhint: "search",
      });
      const submit = (event: Event): void => {
        event.preventDefault();
        const query = input.value.trim();
        const exact = query ? this.exact(ledger, query) : null;
        if (exact) {
          this.go({ project: entry.id, record: exact.id, q: "" }, view);
        } else {
          this.go({ project: entry.id, q: query, page: 1 }, view);
        }
      };
      const kinds = this.kindCounts(ledger).slice(0, 4);
      const latest = ledger.records[0];
      const picker =
        this.projects.length > 1
          ? el(
              "div",
              { class: "lx-projects", role: "group", "aria-label": "Published ledgers" },
              this.projects.map((p) =>
                el("a", { class: "lx-pill", href: this.href({ project: p.id }), "aria-current": p.id === entry.id ? "page" : null }, p.label?.replace(/\s*\(.*\)$/, "") ?? p.id),
              ),
            )
          : null;
      return el(
        "section",
        { class: "lx-hero", "aria-labelledby": "lx-title" },
        entry.sample
          ? el("p", { class: "lx-sample", role: "note" }, icon("eye"), el("span", {}, el("strong", {}, "Sample data. "), "This ledger is invented to show how the explorer reads a project; it describes no real project."))
          : null,
        el("p", { class: "lx-eyebrow" }, icon("lock"), "Open ledger · append-only · checkable"),
        el("h2", { id: "lx-title", class: "lx-title", "data-lx-heading": true }, manifest.project.name),
        el(
          "p",
          { class: "lx-lede" },
          `${plural(manifest.published.records, "record", "records")} of ${number(manifest.seq_range.events)} events are public. `,
          "Open any one, read what happened in plain words, and check it yourself.",
        ),
        picker,
        el("form", { class: "lx-search", role: "search", onsubmit: submit }, icon("search"), el("label", { for: "lx-q", class: "lx-sr" }, "Search this ledger"), input, el("kbd", { class: "lx-key", "aria-hidden": "true" }, "/"), el("button", { type: "submit" }, "Search")),
        el(
          "p",
          { class: "lx-try" },
          el("span", {}, "Try: "),
          latest ? el("a", { class: "lx-chip", href: this.href({ project: entry.id, record: latest.id }) }, `Latest record #${latest.seq}`) : null,
          kinds.map(([kind, count]) => el("a", { class: "lx-chip", href: this.href({ project: entry.id, kind, page: 1 }) }, kindStyle(kind).label, el("span", { class: "lx-count" }, number(count)))),
        ),
      );
    }

    // What was published and what was not, as one bar: the honesty of the ledger at a glance.
    private honesty(manifest: Manifest): HTMLElement {
      const total = Math.max(1, manifest.seq_range.events);
      const segments: Array<{ label: string; count: number; tone: string; why: string }> = [
        { label: "Public", count: manifest.published.records, tone: "public", why: "Published and open to everyone on this page." },
        ...Object.entries(manifest.withheld.by_reason).map(([reason, count]) => {
          const known = REASONS[reason];
          return { label: known?.label ?? reason, count, tone: known?.tone ?? "muted", why: known?.why ?? "" };
        }),
      ].filter((segment) => segment.count > 0);
      const chain = manifest.chain;
      return el(
        "section",
        { class: "lx-card lx-honesty", "aria-labelledby": "lx-honesty-title" },
        el("div", { class: "lx-card-head" }, el("h2", { id: "lx-honesty-title" }, "What you can see, and what you can't"), el("span", { class: `lx-status ${chain.verified ? "lx-ok" : "lx-bad"}` }, icon(chain.verified ? "shield" : "alert"), chain.verified ? `Hash chain verified to #${chain.head_seq ?? "?"}` : `${plural(chain.findings, "chain disagreement", "chain disagreements")}`)),
        el("div", { class: "lx-bar", role: "img", "aria-label": segments.map((s) => `${s.label}: ${number(s.count)} of ${number(total)} events`).join("; ") }, segments.map((s) => el("span", { class: `lx-seg lx-seg-${s.tone}`, style: `flex-grow:${s.count}`, title: `${s.label}: ${number(s.count)}` }))),
        el(
          "ul",
          { class: "lx-legend" },
          segments.map((s) => el("li", {}, el("span", { class: `lx-swatch lx-seg-${s.tone}`, "aria-hidden": "true" }), el("strong", {}, number(s.count)), " ", s.label, el("span", { class: "lx-why" }, ` — ${s.why}`))),
        ),
        el(
          "p",
          { class: "lx-proof" },
          "The chain head covers every event, the hidden ones included, so anyone holding the full ledger can recompute it and confirm this is a true slice of it. ",
          el("span", { class: "lx-hash" }, el("code", { title: chain.head }, short(chain.head)), this.copyButton(chain.head, "chain head")),
        ),
      );
    }

    private tiles(ledger: Ledger): HTMLElement {
      const { records, manifest } = ledger;
      const first = records[records.length - 1];
      const last = records[0];
      const actors = new Set(records.map((r) => r.actor));
      const tile = (name: string, value: string, note: string, glyph: string): HTMLElement =>
        el("div", { class: "lx-tile" }, el("span", { class: "lx-tile-icon" }, icon(glyph)), el("div", {}, el("dt", {}, name), el("dd", {}, el("strong", {}, value), el("span", {}, note))));
      return el(
        "dl",
        { class: "lx-tiles" },
        tile("Public records", number(manifest.published.records), `sequence #${manifest.published.first_seq ?? "—"} to #${manifest.published.last_seq ?? "—"}`, "eye"),
        tile("Kept private", number(manifest.withheld.events), manifest.withheld.events ? "counted, never silently dropped" : "nothing withheld", "lock"),
        tile("Time covered", first && last ? span(first.time, last.time) : "—", first ? `from ${utc(first.time).slice(0, 10)}` : "", "clock"),
        tile("Who acted", number(actors.size), [...actors].slice(0, 3).join(", ") + (actors.size > 3 ? "…" : ""), "users"),
      );
    }

    private kindCounts(ledger: Ledger): Array<[string, number]> {
      const counts = new Map<string, number>();
      ledger.records.forEach((r) => counts.set(r.kind, (counts.get(r.kind) ?? 0) + 1));
      return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    }

    // A search that names one record exactly goes straight to it, like pasting a hash.
    private exact(ledger: Ledger, query: string): IndexEntry | null {
      const q = query.toLowerCase().replace(/^#/, "");
      if (/^\d+$/.test(q)) {
        return ledger.records.find((r) => String(r.seq) === q) ?? null;
      }
      if (/^[0-9a-f-]{12,}$/.test(q)) {
        const hits = ledger.records.filter((r) => r.id === q || r.digest === q);
        return hits.length === 1 ? (hits[0] ?? null) : null;
      }
      return null;
    }

    private matches(ledger: Ledger, view: View): IndexEntry[] {
      const query = view.q.toLowerCase();
      const words = query.split(/[^a-z0-9_]+/).filter(Boolean);
      const prefix = /^[0-9a-f-]{6,}$/.test(query) ? query : null;
      const found = ledger.records.filter((r) => {
        if (view.kind && r.kind !== view.kind) return false;
        if (view.phase && r.phase !== view.phase) return false;
        if (!query) return true;
        if (prefix && (r.id.startsWith(prefix) || r.digest.startsWith(prefix))) return true;
        // Every searched word must begin some word in the record, so "cancel" finds "cancelling".
        return words.every((w) => r.tokens.some((t) => t.startsWith(w)) || kindStyle(r.kind).label.toLowerCase().includes(w) || String(r.seq) === w);
      });
      return view.oldest ? [...found].reverse() : found;
    }

    private records(entry: ProjectEntry, ledger: Ledger, view: View): HTMLElement {
      const found = this.matches(ledger, view);
      const pages = Math.max(1, Math.ceil(found.length / PAGE_SIZE));
      const at = Math.min(view.page, pages);
      const rows = found.slice((at - 1) * PAGE_SIZE, at * PAGE_SIZE);
      const filtered = Boolean(view.q || view.kind || view.phase);
      const change = (c: Partial<View>): string => this.href({ project: entry.id, ...c, page: c.page ?? 1 }, view);

      const kinds = this.kindCounts(ledger);
      const chips = el(
        "div",
        { class: "lx-chips", role: "group", "aria-label": "Filter by kind of record" },
        el("a", { class: "lx-chip", href: change({ kind: "" }), "aria-current": view.kind === "" ? "true" : null }, "All", el("span", { class: "lx-count" }, number(ledger.records.length))),
        kinds.map(([kind, count]) => el("a", { class: `lx-chip lx-tone-${kindStyle(kind).tone}`, href: change({ kind: view.kind === kind ? "" : kind }), "aria-current": view.kind === kind ? "true" : null }, icon(kindStyle(kind).icon), kindStyle(kind).label, el("span", { class: "lx-count" }, number(count)))),
      );

      const live = el("p", { class: "lx-result-line", "aria-live": "polite" }, found.length === 0 ? "No records match." : `Showing ${number((at - 1) * PAGE_SIZE + 1)}–${number((at - 1) * PAGE_SIZE + rows.length)} of ${plural(found.length, "record", "records")}${view.q ? ` for “${view.q}”` : ""}`);
      const tools = el(
        "div",
        { class: "lx-tools" },
        live,
        filtered ? el("a", { class: "lx-link", href: this.href({ project: entry.id }) }, "Clear filters") : null,
        el("a", { class: "lx-link", href: change({ oldest: !view.oldest }) }, view.oldest ? "Oldest first ↑" : "Newest first ↓"),
      );

      let content: HTMLElement;
      if (found.length === 0) {
        content = this.empty(
          filtered ? "Nothing public matches that" : "No records are public yet",
          filtered ? "Records the policy withheld can never be found here, by design; the bar above counts them. Try fewer words, or clear the filters." : "Everything in this ledger is currently withheld.",
          filtered ? this.href({ project: entry.id }) : undefined,
          filtered ? "Clear filters" : undefined,
        );
      } else {
        const tbody = el("tbody", {});
        for (const record of rows) {
          tbody.append(this.row(entry, ledger, view, record));
        }
        content = el(
          "div",
          { class: "lx-scroll" },
          el("table", { class: "lx-table" }, el("caption", { class: "lx-sr" }, "Public records of this ledger"), el("thead", {}, el("tr", {}, ["#", "What happened", "Phase", "Who", "When", "Digest"].map((h) => el("th", { scope: "col" }, h)))), tbody),
        );
      }

      return el(
        "section",
        { class: "lx-card lx-records", "aria-labelledby": "lx-records-title" },
        el("div", { class: "lx-card-head" }, el("h2", { id: "lx-records-title" }, "Records"), this.phaseStrip(entry, ledger, view)),
        chips,
        tools,
        content,
        pages > 1 ? this.pager(entry, view, at, pages) : null,
      );
    }

    // Where in the arc of the work the records sit, as segments you can press to narrow to a phase.
    private phaseStrip(entry: ProjectEntry, ledger: Ledger, view: View): HTMLElement {
      const first = new Map<string, number>();
      const counts = new Map<string, number>();
      for (const r of ledger.records) {
        counts.set(r.phase, (counts.get(r.phase) ?? 0) + 1);
        first.set(r.phase, Math.min(first.get(r.phase) ?? Number.POSITIVE_INFINITY, r.seq));
      }
      const phases = [...counts.keys()].sort((a, b) => (first.get(a) ?? 0) - (first.get(b) ?? 0));
      return el(
        "div",
        { class: "lx-phases", role: "group", "aria-label": "Filter by phase of the work" },
        phases.map((phase) =>
          el("a", { class: "lx-phase", style: `flex-grow:${counts.get(phase) ?? 1}`, href: this.href({ project: entry.id, phase: view.phase === phase ? "" : phase, page: 1 }, view), "aria-current": view.phase === phase ? "true" : null, title: `${phase}: ${plural(counts.get(phase) ?? 0, "record", "records")}` }, phase.replace(/_/g, " ")),
        ),
      );
    }

    private row(entry: ProjectEntry, ledger: Ledger, view: View, record: IndexEntry): HTMLElement {
      const summary = el("span", { class: "lx-summary lx-skel-text" }, "Loading…");
      void this.store.document(ledger, record.id).then(
        (doc) => {
          const text = summarise(record.kind, doc.record.payload);
          summary.textContent = text ? clip(text, 160) : "No further detail was recorded";
          summary.classList.remove("lx-skel-text");
          summary.classList.toggle("lx-dim", !text);
        },
        () => {
          summary.textContent = "Open the record to read it";
          summary.classList.remove("lx-skel-text");
        },
      );
      const link = this.href({ project: entry.id, record: record.id }, view);
      return el(
        "tr",
        { class: "lx-row", onclick: (event: Event) => ((event.target as HTMLElement).closest("a,button") ? undefined : (window.location.hash = link)) },
        el("td", { class: "lx-num", "data-label": "Sequence" }, el("a", { href: link, "aria-label": `Open record ${record.seq}` }, `#${record.seq}`)),
        el("td", { "data-label": "What happened" }, el("div", { class: "lx-what" }, this.badge(record.kind), summary)),
        el("td", { "data-label": "Phase" }, el("span", { class: "lx-phase-name" }, record.phase.replace(/_/g, " "))),
        el("td", { "data-label": "Who" }, record.actor),
        el("td", { class: "lx-when", "data-label": "When" }, el("time", { datetime: record.time, title: utc(record.time) }, relative(record.time))),
        el("td", { class: "lx-hash", "data-label": "Digest" }, el("code", { title: record.digest }, short(record.digest))),
      );
    }

    private pager(entry: ProjectEntry, view: View, at: number, pages: number): HTMLElement {
      const to = (page: number): string => this.href({ project: entry.id, page }, view);
      const numbers: number[] = [...new Set([1, at - 1, at, at + 1, pages].filter((n) => n >= 1 && n <= pages))].sort((a, b) => a - b);
      const items: Child[] = [];
      numbers.forEach((n, i) => {
        const before = numbers[i - 1];
        if (before !== undefined && n - before > 1) items.push(el("span", { class: "lx-gap", "aria-hidden": "true" }, "…"));
        items.push(el("a", { class: "lx-page-link", href: to(n), "aria-current": n === at ? "page" : null, "aria-label": `Page ${n}` }, String(n)));
      });
      return el(
        "nav",
        { class: "lx-pager", "aria-label": "Pages of records" },
        at > 1 ? el("a", { class: "lx-button lx-button-quiet", href: to(at - 1), rel: "prev" }, icon("arrowLeft"), "Previous") : el("span", {}),
        el("div", { class: "lx-pages" }, items),
        at < pages ? el("a", { class: "lx-button lx-button-quiet", href: to(at + 1), rel: "next" }, "Next", icon("arrowRight")) : el("span", {}),
      );
    }

    private footnote(manifest: Manifest): HTMLElement {
      const w = manifest.withheld;
      return el(
        "section",
        { class: "lx-foot" },
        el("p", {}, `Inside the public records, ${plural(w.fields, "field", "fields")} ${w.fields === 1 ? "was" : "were"} withheld, ${plural(w.paths, "absolute path", "absolute paths")} and ${plural(w.emails, "email address", "email addresses")} stripped, and ${plural(w.credentials, "record", "records")} had a credential redacted. `, el("a", { href: this.guide }, "Exactly what gets published"), "."),
        el("p", { class: "lx-keys" }, el("kbd", {}, "/"), " search  ", el("kbd", {}, "←"), el("kbd", {}, "→"), " walk the ledger  ", el("kbd", {}, "Esc"), " back"),
      );
    }

    // ---- one record -------------------------------------------------------------------------
    private async recordView(entry: ProjectEntry, ledger: Ledger, view: View): Promise<HTMLElement> {
      const id = view.record ?? "";
      let doc: RecordDocument;
      try {
        doc = await this.store.document(ledger, id);
      } catch {
        return el("div", { class: "lx-page" }, this.empty("That record is not public", "It may be one the publication policy withheld, which is never shown, or the link may be mistyped.", this.lastList || this.href({ project: entry.id }), "Back to the records"));
      }
      const r = doc.record;
      const style = kindStyle(r.kind);
      const summary = summarise(r.kind, r.payload);
      const index = ledger.records.find((x) => x.id === r.event_id);
      const causation = r.causation_id ? ledger.records.find((x) => x.id === r.causation_id) : undefined;
      const back = this.lastList || this.href({ project: entry.id });
      const step = (neighbour: Neighbour | null, label: string, glyph: string, side: "prev" | "next"): HTMLElement =>
        neighbour
          ? el("a", { class: "lx-button lx-button-quiet", href: this.href({ project: entry.id, record: neighbour.event_id }, view), rel: side }, side === "prev" ? icon(glyph) : null, `${label} #${neighbour.seq}`, side === "next" ? icon(glyph) : null)
          : el("span", { class: "lx-button lx-button-quiet lx-disabled", "aria-disabled": "true" }, label, " — none");

      const check = el("span", { class: "lx-status lx-pending" }, el("span", { class: "lx-spin", "aria-hidden": "true" }), "Checking the digest in your browser…");
      void this.verify(r).then((result) => check.replaceWith(result));

      const raw = JSON.stringify(r.payload, null, 2);
      const rawBox = el("pre", { class: "lx-json", tabindex: "0", hidden: true }, raw);
      const rawButton = el("button", { type: "button", class: "lx-link lx-toggle", "aria-expanded": "false", onclick: () => {
        const open = rawBox.hasAttribute("hidden");
        rawBox.toggleAttribute("hidden", !open);
        rawButton.setAttribute("aria-expanded", String(open));
        rawButton.textContent = open ? "Hide raw JSON" : "Show raw JSON";
      } }, "Show raw JSON");

      const fact = (name: string, value: Child): HTMLElement => el("div", { class: "lx-fact" }, el("dt", {}, name), el("dd", {}, value));
      return el(
        "article",
        { class: "lx-page lx-record" },
        el("nav", { class: "lx-crumbs", "aria-label": "Breadcrumb" }, el("a", { href: back }, icon("arrowLeft"), "All records"), el("span", { "aria-hidden": "true" }, "/"), el("span", {}, entry.sample ? "sample ledger" : ledger.manifest.project.name)),
        el(
          "header",
          { class: "lx-card lx-record-head" },
          el("div", { class: "lx-record-top" }, el("span", { class: "lx-seq" }, `#${r.seq}`), this.badge(r.kind), index ? el("span", { class: "lx-when" }, el("time", { datetime: index.time, title: utc(index.time) }, relative(index.time))) : null),
          el("h2", { class: "lx-record-title", "data-lx-heading": true }, summary ? clip(summary, 220) : style.label),
          el("p", { class: "lx-meta" }, `${r.phase.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())} phase · cycle ${r.cycle} · ${r.engine_id ?? "vibey itself"} · ${r.provenance}`),
          el("div", { class: "lx-step" }, step(doc.previous, "Earlier", "arrowLeft", "prev"), step(doc.next, "Later", "arrowRight", "next")),
        ),
        el(
          "section",
          { class: "lx-card", "aria-labelledby": "lx-body-title" },
          el("div", { class: "lx-card-head" }, el("h2", { id: "lx-body-title" }, "What was recorded"), rawButton),
          this.payload(r.payload),
          rawBox,
        ),
        el(
          "section",
          { class: "lx-card", "aria-labelledby": "lx-proof-title" },
          el("div", { class: "lx-card-head" }, el("h2", { id: "lx-proof-title" }, "Proof and place"), check),
          el(
            "dl",
            { class: "lx-facts" },
            fact("Digest (SHA-256)", el("span", { class: "lx-hash" }, el("code", { class: "lx-wrap" }, r.digest), this.copyButton(r.digest, "digest"))),
            fact("Event id", el("span", { class: "lx-hash" }, el("code", { class: "lx-wrap" }, r.event_id), this.copyButton(r.event_id, "event id"))),
            fact("Recorded at", `${utc(r.produced_at)}`),
            fact("Caused by", r.causation_id ? (causation ? el("a", { href: this.href({ project: entry.id, record: r.causation_id }, view) }, `#${causation.seq} · ${kindStyle(causation.kind).label}`) : el("span", {}, "an event that is not public")) : "nothing: this began the run"),
            fact("Run", el("span", { class: "lx-hash" }, el("code", { class: "lx-wrap" }, short(r.correlation_id)), this.copyButton(r.correlation_id, "run id"))),
          ),
          el("p", { class: "lx-note" }, `Removed from this record before publishing: ${plural(doc.withheld.fields, "field", "fields")}, ${plural(doc.withheld.paths, "absolute path", "absolute paths")}, ${plural(doc.withheld.emails, "email address", "email addresses")}, ${plural(doc.withheld.credentials, "credential", "credentials")}. `, el("a", { href: this.guide }, "What gets published"), "."),
        ),
        el("p", { class: "lx-keys" }, el("kbd", {}, "←"), el("kbd", {}, "→"), " earlier and later  ", el("kbd", {}, "Esc"), " back to the list"),
      );
    }

    // The payload in readable form: names and values, nested things indented. Text only.
    private payload(value: unknown): HTMLElement {
      const label = (key: string): string => key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
      const render = (v: unknown): Child => {
        if (v === null || v === undefined) return el("span", { class: "lx-dim" }, "none");
        if (typeof v === "boolean") return el("span", { class: `lx-tag ${v ? "lx-ok" : "lx-bad"}` }, v ? "yes" : "no");
        if (typeof v === "number") return String(v);
        if (typeof v === "string") return el("span", { class: "lx-text" }, v);
        if (Array.isArray(v)) return v.length === 0 ? el("span", { class: "lx-dim" }, "empty") : el("ul", { class: "lx-list" }, v.map((x) => el("li", {}, render(x))));
        return el("dl", { class: "lx-nested" }, Object.entries(v as Record<string, unknown>).map(([k, x]) => el("div", { class: "lx-fact" }, el("dt", {}, label(k)), el("dd", {}, render(x)))));
      };
      if (value === null || typeof value !== "object" || Array.isArray(value)) {
        return el("div", { class: "lx-body" }, render(value));
      }
      return el("div", { class: "lx-body" }, render(value));
    }

    // Hash the payload the way the exporter did and compare with the digest the record claims.
    private async verify(record: RecordFields): Promise<HTMLElement> {
      if (!window.crypto || !window.crypto.subtle) {
        return el("span", { class: "lx-status lx-pending" }, icon("alert"), "Not checked: this browser has no SubtleCrypto here (it needs https).");
      }
      try {
        const got = await sha256(canonical(record.payload));
        return got === record.digest
          ? el("span", { class: "lx-status lx-ok", role: "status" }, icon("shield"), "Digest matches: your browser just recomputed it")
          : el("span", { class: "lx-status lx-bad", role: "alert" }, icon("alert"), `This browser computed ${short(got)}, not the digest shown. A payload with a decimal number can serialise differently here than in Python; otherwise the record was altered.`);
      } catch (error) {
        return el("span", { class: "lx-status lx-pending" }, icon("alert"), `Not checked: ${error instanceof Error ? error.message : String(error)}`);
      }
    }
  }

  const mount = document.getElementById("ledger-explorer-app");
  if (mount) {
    // The documentation theme gives a page a narrow reading column; an explorer wants the width.
    document.body.classList.add("lx-wide");
    const base = (mount.dataset.base ?? "data/").replace(/\/?$/, "/");
    const guide = mount.dataset.guide ?? "../guides/ledger-publication/";
    void new LedgerExplorer(mount, new LedgerStore(base), guide).start();
  }
})();
