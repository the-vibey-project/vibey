// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The task panel's page. Everything it shows came from a model, a tool or vibey, so it is
// rendered with textContent only: nothing here ever parses a string as HTML.
// TypeScript is the only authored form (sub-doctrine 9.f); scripts/typescript_artifacts.py
// compiles this file to media/panel.js, the script the webview loads.

declare function acquireVsCodeApi(): { postMessage(message: unknown): void };

(() => {
  interface SlashCommand {
    name: string;
    usage: string;
    description: string;
  }
  interface PanelGate {
    gateId: string;
    kind: string;
    prompt: string;
    projectName: string;
    isSpend: boolean;
    choices: { label: string; command: string }[];
  }
  type PanelItem =
    | { id: number; kind: "assistant"; text: string }
    | { id: number; kind: "tool-call"; name: string; detail?: string }
    | { id: number; kind: "tool-result"; ok: boolean; detail: string }
    | { id: number; kind: "turn"; detail: string }
    | { id: number; kind: "follow-up"; text: string }
    | { id: number; kind: "notice"; text: string; level?: string }
    | { id: number; kind: "thought"; text: string; duration?: number };

  type PanelPatch = { op: "add"; item: PanelItem } | { op: "append"; id: number; text: string };
  interface ModelConfig {
    name: string;
    effort: string;
    ultracode: boolean;
    models?: string[];
  }
  interface StatusFields {
    status: string;
    forceAfterMs?: number;
    finishedActions?: boolean;
    takesFollowUps?: boolean;
    model?: ModelConfig;
    agentMode?: string;
    sessionDuration?: string;
    subagentsCount?: number;
    browserConnected?: boolean;
  }
  type HostMessage =
    | ({ type: "init"; title: string; slash: SlashCommand[]; canPasteImage: boolean; items: PanelItem[]; gates?: PanelGate[] } & StatusFields)
    | { type: "gates"; gates: PanelGate[] }
    | { type: "items"; items: PanelItem[] }
    | { type: "patch"; patch: PanelPatch }
    | ({ type: "status" } & StatusFields)
    | { type: "config"; model?: ModelConfig; agentMode?: string; browserConnected?: boolean }
    | { type: "note"; level: string; text: string }
    | { type: "look"; theme?: string; surface?: string; ultra?: boolean; unlimited?: boolean };

  const vscode = acquireVsCodeApi();
  const $ = <T extends HTMLElement = HTMLElement>(id: string): T => document.getElementById(id) as T;

  const gatesBox = $("gates");
  const itemsBox = $("items");
  const input = $<HTMLTextAreaElement>("input");
  const completions = $("completions");
  const chipsBox = $("chips");
  const statusLine = $("status");
  const title = $("title");
  const banner = $("banner");
  const effortPill = $("effort");
  const browserBanner = $("browserBanner");
  const closeBrowserBanner = $("closeBrowserBanner");
  const activityIndicator = $("activityIndicator");
  const activityText = $("activityText");
  const finishedActions = $("finishedActions");

  const btnAdd = $("btnAdd");
  const btnActions = $("btnActions");
  const btnModelSelect = $("btnModelSelect");
  const btnModeSelect = $("btnModeSelect");
  const btnRemoteControl = $("btnRemoteControl");
  const btnMic = $("btnMic");
  const btnBookmark = $("btnBookmark");
  const btnHistory = $("btnHistory");
  const btnNewChat = $("btnNewChat");

  const popoverAdd = $("popoverAdd");
  const popoverActions = $("popoverActions");
  const popoverModel = $("popoverModel");
  const popoverMode = $("popoverMode");

  const modelName = $("modelName");
  const modelEffort = $("modelEffort");
  const modeName = $("modeName");
  const sessionTimer = $("sessionTimer");
  const agentCount = $("agentCount");
  const actionSearch = $<HTMLInputElement>("actionSearch");
  const effortRange = $<HTMLInputElement>("effortRange");
  const modeEffortRange = $<HTMLInputElement>("modeEffortRange");
  const actionEffortLabel = $("actionEffortLabel");
  const actionUltracodeToggle = $<HTMLInputElement>("actionUltracodeToggle");
  const modelUltracodeToggle = $<HTMLInputElement>("modelUltracodeToggle");
  const modeUltracodeToggle = $<HTMLInputElement>("modeUltracodeToggle");

  const buttons = {
    start: $<HTMLButtonElement>("start"),
    stop: $<HTMLButtonElement>("stop"),
    force: $<HTMLButtonElement>("force"),
    review: $<HTMLButtonElement>("review"),
    apply: $<HTMLButtonElement>("apply"),
    discard: $<HTMLButtonElement>("discard"),
  };

  const shown = new Map<number, HTMLElement>();
  const toolCallElements = new Map<string, HTMLElement>();
  let slash: SlashCommand[] = [];
  let canPasteImage = false;
  let forceTimer = 0;
  let status = "idle";
  let takesFollowUps = false;
  let chosen = -1;
  let currentModel = "Sonnet 5.5";
  let currentEffort = "Medium";
  let currentMode = "Auto";
  let isUltracode = false;

  const EFFORT_NAMES = ["", "Low", "Medium", "High", "Ultra"];

  const WORDS: Readonly<Record<string, string>> = {
    idle: "Ready to chat, answer gates, or run a task.",
    queued: "Waiting its turn for the model.",
    preparing: "Making its copy of the folder.",
    waiting: "Waiting for the model.",
    running: "Running. Type to tell it something; it reads it at its next turn.",
    stopping: "Stopping: the model finishes the turn it is on.",
    finishing: "Finishing: committing the work on its branch.",
    finished: "Finished.",
    lane: "Watching a lane started elsewhere (read-only).",
  };

  const renderGates = (gates: PanelGate[]): void => {
    gatesBox.replaceChildren();
    gatesBox.hidden = gates.length === 0;
    for (const gate of gates) {
      const card = document.createElement("div");
      card.className = `gate-card${gate.isSpend ? " spend" : ""}`;
      const header = document.createElement("div");
      header.className = "gate-header";
      const badge = document.createElement("span");
      badge.className = `gate-badge${gate.isSpend ? " spend" : ""}`;
      badge.textContent = gate.isSpend ? "SPEND GATE · requires spend scope" : "Gate · answer scope";
      const meta = document.createElement("span");
      meta.className = "gate-meta";
      meta.textContent = `${gate.projectName} · ${gate.kind}`;
      header.append(badge, meta);
      const prompt = document.createElement("div");
      prompt.className = "gate-prompt";
      prompt.textContent = gate.prompt;
      const actions = document.createElement("div");
      actions.className = "gate-actions";
      for (const choice of gate.choices) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = gate.isSpend ? "quiet spend-choice" : "quiet";
        button.textContent = choice.label;
        button.addEventListener("click", () => {
          vscode.postMessage({ type: "send", text: choice.command });
        });
        actions.append(button);
      }
      card.append(header, prompt, actions);
      gatesBox.append(card);
    }
  };

  const createThoughtCard = (text: string, durationSec = 5): HTMLElement => {
    const card = document.createElement("div");
    card.className = "thought-card";
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "thought-toggle";
    toggle.setAttribute("aria-expanded", "false");

    const dot = document.createElement("span");
    dot.className = "thought-dot";
    dot.textContent = "●";

    const label = document.createElement("span");
    label.className = "thought-label";
    label.textContent = `Thought for ${durationSec}s`;

    const chevron = document.createElement("span");
    chevron.className = "thought-chevron";
    chevron.textContent = "▾";

    toggle.append(dot, label, chevron);

    const content = document.createElement("div");
    content.className = "thought-content";
    content.hidden = true;
    content.textContent = text || "Reasoning through solution constraints, AST purity, and model rotation...";

    toggle.addEventListener("click", () => {
      const expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      content.hidden = expanded;
      chevron.textContent = expanded ? "▾" : "▴";
    });

    card.append(toggle, content);
    return card;
  };

  const createToolCallCard = (name: string, detail?: string): HTMLElement => {
    const card = document.createElement("div");
    card.className = "tool-call-card";

    const header = document.createElement("div");
    header.className = "tool-call-header";

    const left = document.createElement("div");
    left.className = "tool-header-left";

    const tag = document.createElement("span");
    tag.className = "tool-tag";
    tag.textContent = name;

    const titleEl = document.createElement("span");
    titleEl.className = "tool-title";
    titleEl.textContent = detail ? ` ${detail}` : "";

    left.append(tag, titleEl);

    const btnRunBg = document.createElement("button");
    btnRunBg.type = "button";
    btnRunBg.className = "btn-run-bg";
    btnRunBg.textContent = "Run in background";
    btnRunBg.addEventListener("click", () => {
      vscode.postMessage({ type: "note", level: "info", text: `Tool ${name} continues in background.` });
    });

    header.append(left, btnRunBg);

    const body = document.createElement("div");
    body.className = "tool-call-body";

    const inSection = document.createElement("div");
    inSection.className = "tool-section in";
    const inLabel = document.createElement("span");
    inLabel.className = "section-label";
    inLabel.textContent = "IN";
    const inPre = document.createElement("pre");
    inPre.className = "code-box in-box";
    inPre.textContent = detail ?? name;
    inSection.append(inLabel, inPre);

    const outSection = document.createElement("div");
    outSection.className = "tool-section out";
    outSection.hidden = true;
    const outLabel = document.createElement("span");
    outLabel.className = "section-label";
    outLabel.textContent = "OUT";
    const outPre = document.createElement("pre");
    outPre.className = "code-box out-box";
    outSection.append(outLabel, outPre);

    body.append(inSection, outSection);
    card.append(header, body);

    toolCallElements.set(name, outSection);
    return card;
  };

  const createFollowUpCard = (text: string): HTMLElement => {
    const card = document.createElement("div");
    card.className = "user-message-card";

    const header = document.createElement("div");
    header.className = "user-message-header";

    const label = document.createElement("span");
    label.className = "user-label";
    label.textContent = "You";

    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    const timestamp = document.createElement("span");
    timestamp.className = "user-timestamp";
    timestamp.textContent = timeStr;

    header.append(label, timestamp);

    const body = document.createElement("div");
    body.className = "user-message-body";
    body.textContent = text;

    card.append(header, body);
    return card;
  };

  const line = (kind: string, text: string, extra?: string): HTMLElement => {
    const element = document.createElement(kind === "assistant" ? "div" : "div");
    element.className = `item ${kind}${extra ? ` ${extra}` : ""}`;
    element.textContent = text;
    return element;
  };

  const render = (item: PanelItem): HTMLElement => {
    switch (item.kind) {
      case "assistant": {
        const wrapper = document.createElement("div");
        wrapper.className = "assistant-block";
        const content = document.createElement("div");
        content.className = "assistant-narration";
        content.textContent = item.text;
        wrapper.append(content);
        return wrapper;
      }
      case "thought":
        return createThoughtCard(item.text, item.duration ?? 5);
      case "tool-call":
        return createToolCallCard(item.name, item.detail);
      case "tool-result": {
        const lastTool = toolCallElements.get(item.detail) ?? Array.from(toolCallElements.values()).pop();
        if (lastTool) {
          lastTool.hidden = false;
          const pre = lastTool.querySelector("pre");
          if (pre) {
            pre.textContent = item.detail;
          }
        }
        return line("tool-result", `${item.ok ? "✓" : "✗"} ${item.detail}`, item.ok ? "" : "failed");
      }
      case "turn":
        return line("turn", item.detail);
      case "follow-up":
        return createFollowUpCard(item.text);
      case "notice":
        return line("notice", item.text, item.level);
      default:
        return line("notice", `Item: ${String((item as { kind: unknown }).kind)}`, "warn");
    }
  };

  const add = (item: PanelItem): void => {
    const element = render(item);
    shown.set(item.id, element);
    itemsBox.insertBefore(element, activityIndicator);
  };

  const follow = (): (() => void) => {
    const near = itemsBox.scrollHeight - itemsBox.scrollTop - itemsBox.clientHeight < 120;
    return () => {
      if (near) {
        itemsBox.scrollTop = itemsBox.scrollHeight;
      }
    };
  };

  const replaceItems = (items: PanelItem[]): void => {
    const scroll = follow();
    shown.clear();
    toolCallElements.clear();
    itemsBox.replaceChildren(activityIndicator);
    for (const item of items) {
      add(item);
    }
    scroll();
  };

  const patch = (change: PanelPatch): void => {
    const scroll = follow();
    if (change.op === "add") {
      add(change.item);
    } else {
      const element = shown.get(change.id);
      if (element) {
        const narration = element.querySelector(".assistant-narration") ?? element;
        narration.textContent += change.text;
      }
    }
    scroll();
  };

  const note = (level: string, text: string): void => {
    const scroll = follow();
    itemsBox.insertBefore(line("notice", text, level), activityIndicator);
    scroll();
  };

  const closeAllPopovers = (): void => {
    popoverAdd.hidden = true;
    popoverActions.hidden = true;
    popoverModel.hidden = true;
    popoverMode.hidden = true;
  };

  const togglePopover = (popover: HTMLElement): void => {
    const willOpen = popover.hidden;
    closeAllPopovers();
    popover.hidden = !willOpen;
    if (!popover.hidden && popover === popoverActions) {
      actionSearch.value = "";
      filterActions("");
      actionSearch.focus();
    }
  };

  const setStatus = (next: string, forceAfterMs?: number, finishedActionsFlag?: boolean, followUps?: boolean): void => {
    status = next;
    takesFollowUps = followUps === true;
    statusLine.textContent = WORDS[next] || next;
    statusLine.dataset["state"] = next;
    const active = ["queued", "preparing", "waiting", "running", "stopping", "finishing"].includes(next);

    document.body.dataset["live"] = String(["preparing", "waiting", "running", "finishing", "lane"].includes(next));

    buttons.start.hidden = active || next === "lane";
    buttons.stop.hidden = !active || next === "finishing";
    buttons.stop.disabled = next === "stopping";

    activityIndicator.hidden = !active;
    if (active) {
      activityText.textContent = next === "preparing" ? "Framing..." : "Whirring...";
    }

    finishedActions.hidden = !finishedActionsFlag;
    for (const button of [buttons.review, buttons.apply, buttons.discard]) {
      button.hidden = !finishedActionsFlag;
    }

    window.clearTimeout(forceTimer);
    buttons.force.hidden = true;
    if (next === "stopping" && typeof forceAfterMs === "number") {
      forceTimer = window.setTimeout(() => {
        buttons.force.hidden = status !== "stopping";
      }, forceAfterMs);
    }

    const closed = active && next !== "queued" && !takesFollowUps;
    input.disabled = closed;
    input.placeholder = closed
      ? "This engine does not take follow-ups while it runs. Stop is below."
      : next === "running"
        ? "Tell the running task something (Enter sends; Shift+Enter starts a new line), or type / for commands."
        : "Queue another message...";
  };

  const filterActions = (query: string): void => {
    const q = query.trim().toLowerCase();
    const entries = popoverActions.querySelectorAll<HTMLElement>(".action-entry");
    entries.forEach((entry) => {
      const text = entry.textContent?.toLowerCase() ?? "";
      entry.hidden = q !== "" && !text.includes(q);
    });
  };

  const setModel = (name: string): void => {
    currentModel = name;
    modelName.textContent = name;
    popoverModel.querySelectorAll(".model-item").forEach((item) => {
      const match = item.getAttribute("data-model") === name;
      item.classList.toggle("selected", match);
    });
    vscode.postMessage({ type: "action", action: "model", payload: name });
  };

  const setMode = (mode: string): void => {
    currentMode = mode;
    modeName.textContent = mode;
    popoverMode.querySelectorAll(".mode-item").forEach((item) => {
      const match = item.getAttribute("data-mode") === mode;
      item.classList.toggle("selected", match);
    });
    vscode.postMessage({ type: "action", action: "mode", payload: mode });
  };

  const setEffort = (val: number): void => {
    const label = EFFORT_NAMES[val] || "Medium";
    currentEffort = label;
    modelEffort.textContent = label;
    actionEffortLabel.textContent = label;
    effortRange.value = String(val);
    modeEffortRange.value = String(val);
    vscode.postMessage({ type: "action", action: "effort", payload: label.toUpperCase() });
  };

  const setUltracode = (on: boolean): void => {
    isUltracode = on;
    actionUltracodeToggle.checked = on;
    modelUltracodeToggle.checked = on;
    modeUltracodeToggle.checked = on;
    document.body.dataset["ultra"] = String(on);
    effortPill.hidden = !on;
    vscode.postMessage({ type: "action", action: "ultracode", payload: on });
  };

  const matches = (): SlashCommand[] => {
    const typed = input.value;
    if (!typed.startsWith("/") || /\s/.test(typed)) {
      return [];
    }
    const partial = typed.slice(1).toLowerCase();
    return slash.filter((command) => command.name.startsWith(partial)).slice(0, 12);
  };

  const complete = (command: SlashCommand): void => {
    input.value = `/${command.name} `;
    completions.hidden = true;
    input.focus();
  };

  const showCompletions = (): void => {
    const found = matches();
    completions.replaceChildren();
    completions.hidden = found.length === 0;
    chosen = found.length === 0 ? -1 : Math.min(Math.max(chosen, 0), found.length - 1);
    found.forEach((command, index) => {
      const option = document.createElement("li");
      option.setAttribute("role", "option");
      option.className = index === chosen ? "chosen" : "";
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = `/${command.name}${command.usage ? ` ${command.usage}` : ""}`;
      const description = document.createElement("span");
      description.className = "description";
      description.textContent = command.description;
      option.append(name, description);
      option.addEventListener("mousedown", (event) => {
        event.preventDefault();
        complete(command);
      });
      completions.append(option);
    });
  };

  const send = (): void => {
    const text = input.value.trim();
    if (!text) {
      return;
    }
    add({ id: Date.now(), kind: "follow-up", text });
    vscode.postMessage({ type: "send", text });
    input.value = "";
    completions.hidden = true;
    closeAllPopovers();
  };

  input.addEventListener("keydown", (event) => {
    if (event.isComposing || event.keyCode === 229) {
      return;
    }
    const found = completions.hidden ? [] : matches();
    if (found.length > 0 && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      chosen = (chosen + (event.key === "ArrowDown" ? 1 : found.length - 1)) % found.length;
      showCompletions();
      return;
    }
    const pick = found[Math.max(chosen, 0)];
    if (pick && event.key === "Tab") {
      event.preventDefault();
      complete(pick);
      return;
    }
    if (event.key === "Escape") {
      completions.hidden = true;
      closeAllPopovers();
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  });

  input.addEventListener("input", showCompletions);
  input.addEventListener("blur", () => {
    completions.hidden = true;
  });

  // Popover triggers
  btnAdd.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePopover(popoverAdd);
  });
  btnActions.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePopover(popoverActions);
  });
  btnModelSelect.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePopover(popoverModel);
  });
  btnModeSelect.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePopover(popoverMode);
  });

  document.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    if (!target.closest(".popover-menu") && !target.closest(".control-btn") && !target.closest(".select-btn")) {
      closeAllPopovers();
    }
  });

  actionSearch.addEventListener("input", () => {
    filterActions(actionSearch.value);
  });

  // Popover action clicks
  popoverAdd.querySelectorAll<HTMLButtonElement>(".popover-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const act = btn.dataset["action"] ?? "";
      closeAllPopovers();
      vscode.postMessage({ type: "action", action: act });
    });
  });

  popoverActions.querySelectorAll<HTMLButtonElement>(".popover-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const act = btn.dataset["action"] ?? "";
      if (act === "ultracode") {
        return;
      }
      closeAllPopovers();
      vscode.postMessage({ type: "action", action: act });
    });
  });

  popoverModel.querySelectorAll<HTMLButtonElement>(".model-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const m = btn.dataset["model"] ?? "";
      if (m) {
        setModel(m);
      }
      closeAllPopovers();
    });
  });

  popoverMode.querySelectorAll<HTMLButtonElement>(".mode-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const mode = btn.dataset["mode"] ?? "";
      if (mode) {
        setMode(mode);
      }
      closeAllPopovers();
    });
  });

  effortRange.addEventListener("input", () => {
    setEffort(Number(effortRange.value));
  });
  modeEffortRange.addEventListener("input", () => {
    setEffort(Number(modeEffortRange.value));
  });

  const toggleUltracode = (event: Event): void => {
    const checked = (event.target as HTMLInputElement).checked;
    setUltracode(checked);
  };
  actionUltracodeToggle.addEventListener("change", toggleUltracode);
  modelUltracodeToggle.addEventListener("change", toggleUltracode);
  modeUltracodeToggle.addEventListener("change", toggleUltracode);

  btnMic.addEventListener("click", () => {
    vscode.postMessage({ type: "note", level: "info", text: "Microphone / voice dictation activated." });
  });

  btnBookmark.addEventListener("click", () => {
    vscode.postMessage({ type: "action", action: "bookmarks" });
  });
  btnHistory.addEventListener("click", () => {
    vscode.postMessage({ type: "button", command: "vibey.showLoops" });
  });
  btnNewChat.addEventListener("click", () => {
    vscode.postMessage({ type: "action", action: "new-chat" });
  });

  btnRemoteControl.addEventListener("click", () => {
    btnRemoteControl.classList.toggle("active");
    const active = btnRemoteControl.classList.contains("active");
    vscode.postMessage({ type: "note", level: "info", text: `Remote Control ${active ? "enabled" : "disabled"}.` });
  });

  closeBrowserBanner.addEventListener("click", () => {
    browserBanner.hidden = true;
  });

  const press = (command: string): (() => void) => () => vscode.postMessage({ type: "button", command });
  buttons.start.addEventListener("click", send);
  buttons.stop.addEventListener("click", press("vibey.stopRun"));
  buttons.force.addEventListener("click", press("vibey.forceStopRun"));
  buttons.review.addEventListener("click", press("vibey.reviewRun"));
  buttons.apply.addEventListener("click", press("vibey.applyRun"));
  buttons.discard.addEventListener("click", press("vibey.discardRun"));
  $("endNoCap").addEventListener("click", press("vibey.endNoCap"));

  for (const button of Array.from(chipsBox.querySelectorAll<HTMLButtonElement>("button.chip"))) {
    button.addEventListener("click", () => {
      const text = button.dataset["slash"] ?? "";
      if (text.endsWith(" ")) {
        input.value = text;
        showCompletions();
        input.focus();
      } else if (text !== "") {
        vscode.postMessage({ type: "send", text });
      }
    });
  }

  const look = (message: Extract<HostMessage, { type: "look" }>): void => {
    const root = document.documentElement;
    root.dataset["theme"] = message.theme === "light" ? "light" : "dark";
    root.dataset["surface"] = message.surface === "krypton" ? "krypton" : "editor";
    document.body.dataset["ultra"] = String(message.ultra === true);
    effortPill.hidden = message.ultra !== true;
    banner.hidden = message.unlimited !== true;
  };

  document.addEventListener("paste", (event) => {
    if (!canPasteImage || !event.clipboardData) {
      return;
    }
    for (const entry of event.clipboardData.items) {
      if (entry.kind === "file" && entry.type.startsWith("image/")) {
        const file = entry.getAsFile();
        if (!file) {
          continue;
        }
        event.preventDefault();
        const reader = new FileReader();
        reader.onload = () => vscode.postMessage({ type: "pasteImage", dataUrl: String(reader.result) });
        reader.readAsDataURL(file);
        return;
      }
    }
  });

  window.addEventListener("message", (event: MessageEvent<HostMessage>) => {
    const message = event.data;
    switch (message.type) {
      case "init":
        title.textContent = message.title;
        slash = message.slash;
        canPasteImage = message.canPasteImage;
        renderGates(message.gates ?? []);
        replaceItems(message.items);
        setStatus(message.status, message.forceAfterMs, message.finishedActions, message.takesFollowUps);
        if (message.model) {
          currentModel = message.model.name;
          modelName.textContent = currentModel;
          currentEffort = message.model.effort;
          modelEffort.textContent = currentEffort;
          isUltracode = message.model.ultracode;
          setUltracode(isUltracode);
        }
        if (message.agentMode) {
          currentMode = message.agentMode;
          modeName.textContent = currentMode;
        }
        if (message.sessionDuration) {
          sessionTimer.textContent = `⏱ ${message.sessionDuration}`;
        }
        if (typeof message.subagentsCount === "number") {
          agentCount.textContent = `${message.subagentsCount} agents`;
        }
        browserBanner.hidden = message.browserConnected !== true;
        input.focus();
        break;
      case "gates":
        renderGates(message.gates);
        break;
      case "items":
        replaceItems(message.items);
        break;
      case "patch":
        patch(message.patch);
        break;
      case "status":
        setStatus(message.status, message.forceAfterMs, message.finishedActions, message.takesFollowUps);
        if (message.model) {
          currentModel = message.model.name;
          modelName.textContent = currentModel;
        }
        break;
      case "config":
        if (message.model) {
          currentModel = message.model.name;
          modelName.textContent = currentModel;
        }
        if (message.agentMode) {
          currentMode = message.agentMode;
          modeName.textContent = currentMode;
        }
        if (message.browserConnected !== undefined) {
          browserBanner.hidden = !message.browserConnected;
        }
        break;
      case "note":
        note(message.level, message.text);
        break;
      case "look":
        look(message);
        break;
    }
  });

  vscode.postMessage({ type: "ready" });
})();
