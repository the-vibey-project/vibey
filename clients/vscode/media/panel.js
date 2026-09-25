// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The task panel's page. Everything it shows came from a model, a tool or vibey, so it is
// rendered with textContent only: nothing here ever parses a string as HTML.
// @ts-check
(function () {
  'use strict';
  // eslint-disable-next-line no-undef
  const vscode = acquireVsCodeApi();
  const $ = (id) => /** @type {HTMLElement} */ (document.getElementById(id));
  const itemsBox = $('items');
  const input = /** @type {HTMLTextAreaElement} */ ($('input'));
  const completions = $('completions');
  const statusLine = $('status');
  const title = $('title');
  const composer = $('composer');
  const buttons = {
    start: $('start'),
    stop: /** @type {HTMLButtonElement} */ ($('stop')),
    force: $('force'),
    review: $('review'),
    apply: $('apply'),
    discard: $('discard'),
  };
  /** @type {Map<number, HTMLElement>} */
  const shown = new Map();
  /** @type {{name: string, usage: string, description: string}[]} */
  let slash = [];
  let canPasteImage = false;
  let forceTimer = 0;
  let status = 'idle';
  let takesFollowUps = false;
  let chosen = -1;

  const WORDS = {
    idle: 'Describe a task to start.',
    queued: 'Waiting its turn for the model.',
    preparing: 'Making its copy of the folder.',
    waiting: 'Waiting for the model.',
    running: 'Running. Type to tell it something; it reads it at its next turn.',
    stopping: 'Stopping: the model finishes the turn it is on.',
    finishing: 'Finishing: committing the work on its branch.',
    finished: 'Finished.',
    lane: 'Watching a lane started elsewhere (read-only).',
  };

  function line(kind, text, extra) {
    const element = document.createElement(kind === 'assistant' ? 'pre' : 'div');
    element.className = `item ${kind}${extra ? ` ${extra}` : ''}`;
    element.textContent = text;
    return element;
  }

  function render(item) {
    switch (item.kind) {
      case 'assistant':
        return line('assistant', item.text);
      case 'tool-call': {
        const element = line('tool-call', '');
        const name = document.createElement('span');
        name.className = 'name';
        name.textContent = item.name;
        element.append(name, document.createTextNode(item.detail ? ` ${item.detail}` : ''));
        return element;
      }
      case 'tool-result':
        return line('tool-result', `${item.ok ? '✓' : '✗'} ${item.detail}`, item.ok ? '' : 'failed');
      case 'turn':
        return line('turn', item.detail);
      case 'follow-up':
        return line('follow-up', `You: ${item.text}`);
      case 'notice':
        return line('notice', item.text, item.level);
      default:
        return line('notice', `An item this page does not know: ${String(item.kind)}`, 'warn');
    }
  }

  function add(item) {
    const element = render(item);
    shown.set(item.id, element);
    itemsBox.append(element);
  }

  function follow() {
    const near = itemsBox.scrollHeight - itemsBox.scrollTop - itemsBox.clientHeight < 80;
    return () => {
      if (near) {
        itemsBox.scrollTop = itemsBox.scrollHeight;
      }
    };
  }

  function replaceItems(items) {
    const scroll = follow();
    shown.clear();
    itemsBox.replaceChildren();
    for (const item of items) {
      add(item);
    }
    scroll();
  }

  function patch(change) {
    const scroll = follow();
    if (change.op === 'add') {
      add(change.item);
    } else {
      const element = shown.get(change.id);
      if (element) {
        element.textContent += change.text;
      }
    }
    scroll();
  }

  function note(level, text) {
    const scroll = follow();
    itemsBox.append(line('notice', text, level));
    scroll();
  }

  function setStatus(next, forceAfterMs, finishedActions, followUps) {
    status = next;
    takesFollowUps = followUps === true;
    statusLine.textContent = WORDS[next] || next;
    const active = ['queued', 'preparing', 'waiting', 'running', 'stopping', 'finishing'].includes(next);
    buttons.start.hidden = active || next === 'lane';
    buttons.stop.hidden = !active || next === 'finishing';
    buttons.stop.disabled = next === 'stopping';
    buttons.stop.textContent = next === 'stopping' ? 'Stopping…' : 'Stop';
    for (const name of ['review', 'apply', 'discard']) {
      buttons[name].hidden = !finishedActions;
    }
    window.clearTimeout(forceTimer);
    buttons.force.hidden = true;
    if (next === 'stopping' && typeof forceAfterMs === 'number') {
      // Force stop is a separate act, offered only once the graceful stop has had its fair time.
      forceTimer = window.setTimeout(() => {
        buttons.force.hidden = status !== 'stopping';
      }, forceAfterMs);
    }
    composer.hidden = next === 'lane';
    // An engine that ignores follow-ups gets no prompt box while it runs: typing would go nowhere.
    const closed = active && next !== 'queued' && !takesFollowUps;
    input.disabled = closed;
    input.placeholder = closed
      ? 'This engine does not take follow-ups while it runs. Stop is below.'
      : next === 'running'
        ? 'Tell the running task something (Enter sends; Shift+Enter starts a new line), or type / for commands.'
        : 'Describe a task, or type / for commands. Enter sends; Shift+Enter starts a new line.';
  }

  function matches() {
    const typed = input.value;
    if (!typed.startsWith('/') || /\s/.test(typed)) {
      return [];
    }
    const partial = typed.slice(1).toLowerCase();
    return slash.filter((command) => command.name.startsWith(partial)).slice(0, 12);
  }

  function showCompletions() {
    const found = matches();
    completions.replaceChildren();
    completions.hidden = found.length === 0;
    chosen = found.length === 0 ? -1 : Math.min(Math.max(chosen, 0), found.length - 1);
    found.forEach((command, index) => {
      const option = document.createElement('li');
      option.setAttribute('role', 'option');
      option.className = index === chosen ? 'chosen' : '';
      const name = document.createElement('span');
      name.className = 'name';
      name.textContent = `/${command.name}${command.usage ? ` ${command.usage}` : ''}`;
      const description = document.createElement('span');
      description.className = 'description';
      description.textContent = command.description;
      option.append(name, description);
      option.addEventListener('mousedown', (event) => {
        event.preventDefault();
        complete(command);
      });
      completions.append(option);
    });
  }

  function complete(command) {
    input.value = `/${command.name} `;
    completions.hidden = true;
    input.focus();
  }

  function send() {
    const text = input.value.trim();
    if (!text) {
      return;
    }
    vscode.postMessage({ type: 'send', text });
    input.value = '';
    completions.hidden = true;
  }

  input.addEventListener('keydown', (event) => {
    // A key that ends an input method's composition belongs to the composition, not to us.
    if (event.isComposing || event.keyCode === 229) {
      return;
    }
    const found = completions.hidden ? [] : matches();
    if (found.length > 0 && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      event.preventDefault();
      chosen = (chosen + (event.key === 'ArrowDown' ? 1 : found.length - 1)) % found.length;
      showCompletions();
      return;
    }
    if (found.length > 0 && event.key === 'Tab') {
      event.preventDefault();
      complete(found[Math.max(chosen, 0)]);
      return;
    }
    if (event.key === 'Escape') {
      completions.hidden = true;
      return;
    }
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  });
  input.addEventListener('input', showCompletions);
  input.addEventListener('blur', () => {
    completions.hidden = true;
  });

  buttons.start.addEventListener('click', send);
  buttons.stop.addEventListener('click', () => vscode.postMessage({ type: 'button', command: 'vibey.stopRun' }));
  buttons.force.addEventListener('click', () => vscode.postMessage({ type: 'button', command: 'vibey.forceStopRun' }));
  buttons.review.addEventListener('click', () => vscode.postMessage({ type: 'button', command: 'vibey.reviewRun' }));
  buttons.apply.addEventListener('click', () => vscode.postMessage({ type: 'button', command: 'vibey.applyRun' }));
  buttons.discard.addEventListener('click', () => vscode.postMessage({ type: 'button', command: 'vibey.discardRun' }));

  document.addEventListener('paste', (event) => {
    if (!canPasteImage || !event.clipboardData) {
      return;
    }
    for (const entry of event.clipboardData.items) {
      if (entry.kind === 'file' && entry.type.startsWith('image/')) {
        const file = entry.getAsFile();
        if (!file) {
          continue;
        }
        event.preventDefault();
        const reader = new FileReader();
        reader.onload = () => vscode.postMessage({ type: 'pasteImage', dataUrl: String(reader.result) });
        reader.readAsDataURL(file);
        return;
      }
    }
  });

  window.addEventListener('message', (event) => {
    const message = event.data;
    switch (message.type) {
      case 'init':
        title.textContent = message.title;
        slash = message.slash;
        canPasteImage = message.canPasteImage;
        replaceItems(message.items);
        setStatus(message.status, message.forceAfterMs, message.finishedActions, message.takesFollowUps);
        input.focus();
        break;
      case 'items':
        replaceItems(message.items);
        break;
      case 'patch':
        patch(message.patch);
        break;
      case 'status':
        setStatus(message.status, message.forceAfterMs, message.finishedActions, message.takesFollowUps);
        break;
      case 'note':
        note(message.level, message.text);
        break;
    }
  });

  vscode.postMessage({ type: 'ready' });
})();
