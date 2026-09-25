// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The one table of commands. package.json's `contributes.commands`, the command menu behind
 * the status bar, the task panel's `/` commands and the `@vibey` chat participant's commands
 * all come from it, and unit tests hold package.json and the README to it, so the four can
 * never drift. Every button and key in the editor runs one of these, so every action has
 * one implementation. Declared by `interfaces/commands-interface.ts`.
 */
import { Efforts } from './catalogue';
import type { EffortSetting, LoopName } from './interfaces/catalogue-interface';
import type {
  CommandGroup,
  CommandSpec,
  SlashArgumentsInterface,
  SlashCommandsInterface,
  SlashParse,
} from './interfaces/commands-interface';

export class CommandTable {
  static readonly GROUPS: readonly CommandGroup[] = ['Run', 'Loop & model', 'Lanes', 'Projects & gates', 'Budgets', 'Ollama', 'Doctor'];

  static readonly ALL: readonly CommandSpec[] = [
    {
      id: 'vibey.ask',
      title: 'Ask the model to do a task',
      group: 'Run',
      icon: 'comment-discussion',
      slash: 'ask',
      usage: '<task>',
      description: 'Start a task on a copy of your folder; nothing changes until you apply it.',
      example: '/ask add a line to README.md that says how to run the tests',
      wraps: 'gptossloop run (or the chosen loop engine)',
    },
    {
      id: 'vibey.followUp',
      title: 'Tell the running task something',
      group: 'Run',
      icon: 'reply',
      slash: 'tell',
      usage: '<message>',
      description: 'Send a follow-up to the task that is running; the model reads it at its next turn.',
      example: '/tell keep the heading short',
      wraps: 'gptossloop prompt (or the running engine\'s)',
    },
    {
      id: 'vibey.runBatch',
      title: 'Run a folder of tasks',
      group: 'Run',
      icon: 'checklist',
      slash: 'batch',
      usage: '<folder>',
      description: 'Run every .md task file in a folder, one at a time, each on its own branch; run it again to resume.',
      example: '/batch docs/tasks',
    },
    {
      id: 'vibey.stopRun',
      title: 'Stop a running task',
      group: 'Run',
      icon: 'debug-stop',
      slash: 'stop',
      usage: '[task id]',
      description: 'Ask a task to wind down: it finishes the turn it is on, then ends.',
      example: '/stop',
      wraps: 'gptossloop stop (or the running engine\'s)',
    },
    {
      id: 'vibey.forceStopRun',
      title: 'Force-stop a task that did not stop',
      group: 'Run',
      icon: 'close',
      slash: 'force-stop',
      usage: '[task id]',
      description: 'End a task at once, only after Stop has waited its fair time; it is written in the journal.',
      example: '/force-stop',
    },
    {
      id: 'vibey.openRunLog',
      title: "Open a task's log",
      group: 'Run',
      icon: 'output',
      slash: 'log',
      usage: '[task id]',
      description: "Open a task's panel: its live stream, or the record of a finished one.",
      example: '/log',
    },
    {
      id: 'vibey.reviewRun',
      title: "Review a finished task's changes",
      group: 'Run',
      icon: 'diff',
      slash: 'review',
      usage: '[task id]',
      description: 'See every change a finished task made, as a diff.',
      example: '/review',
    },
    {
      id: 'vibey.applyRun',
      title: 'Apply a finished task to my branch',
      group: 'Run',
      icon: 'check',
      slash: 'apply',
      usage: '[task id]',
      description: "Merge a finished task's branch into yours; on a conflict nothing is changed.",
      example: '/apply',
      wraps: 'git merge',
    },
    {
      id: 'vibey.discardRun',
      title: 'Discard a finished task',
      group: 'Run',
      icon: 'trash',
      slash: 'discard',
      usage: '[task id]',
      description: "Delete a finished task's copy and branch.",
      example: '/discard',
      wraps: 'git worktree remove, git branch -D',
    },
    {
      id: 'vibey.attachFile',
      title: 'Attach a file to the next task',
      group: 'Run',
      icon: 'file-add',
      slash: 'attach',
      usage: '<path>',
      description: "Copy a file into the task's copy of the folder and point the model at it.",
      example: '/attach ~/Desktop/notes.md',
    },
    {
      id: 'vibey.attachImage',
      title: 'Attach an image to the next task',
      group: 'Run',
      icon: 'file-media',
      slash: 'image',
      usage: '<path>',
      description: 'Only for an engine and model that can see images (for a local model, Ollama must report vision).',
      example: '/image ~/Desktop/screenshot.png',
    },
    {
      id: 'vibey.pasteText',
      title: 'Paste text into the next task',
      group: 'Run',
      icon: 'clippy',
      slash: 'paste',
      usage: '[text]',
      description: 'Add text (or what is on the clipboard) to the next task.',
      example: '/paste Error: cannot find module "x"',
    },
    {
      id: 'vibey.pasteImage',
      title: 'Paste an image into the next task',
      group: 'Run',
      icon: 'device-camera',
      slash: 'paste-image',
      description: 'Only for an engine and model that can see images; paste into the task panel.',
      example: '/paste-image',
    },
    {
      id: 'vibey.plugins',
      title: 'Add vibey-skills context to the next task',
      group: 'Run',
      icon: 'extensions',
      slash: 'plugins',
      usage: '[plugin ...]',
      description: 'Pick plugins from the vibey marketplace; vibey-skills builds a context packet for the task.',
      example: '/plugins frontend-design security-principles',
      wraps: 'vibey-skills packet',
    },
    {
      id: 'vibey.chooseLoop',
      title: 'Choose the loop (sovereign or paid)',
      group: 'Loop & model',
      icon: 'server-environment',
      slash: 'loop',
      usage: 'sovereign|paid',
      description: 'sovereign runs on your own computer, always free; paid uses vendors who bill you, and needs a one-time declaration.',
      example: '/loop sovereign',
    },
    {
      id: 'vibey.chooseEffort',
      title: 'Choose the effort',
      group: 'Loop & model',
      icon: 'dashboard',
      slash: 'effort',
      usage: 'auto|TRIVIAL|LOW|STANDARD|HIGH|MAX|ULTRA',
      description: 'How hard the engine works; auto starts low and climbs one step each time a task fails.',
      example: '/effort auto',
    },
    {
      id: 'vibey.chooseModel',
      title: 'Choose the engine and model',
      group: 'Loop & model',
      icon: 'symbol-class',
      slash: 'model',
      usage: 'auto|<engine>|<engine>/<model>',
      description: 'auto picks by effort within the loop; or name one, such as gptossloop/gpt-oss:20b.',
      example: '/model gptossloop/gpt-oss:20b',
    },
    {
      id: 'vibey.showLoops',
      title: 'Show the loops and engines',
      group: 'Loop & model',
      icon: 'list-tree',
      slash: 'loops',
      description: 'Every loop, engine and what each effort level runs, from vibey.',
      example: '/loops',
      wraps: 'vibey loops --json',
    },
    {
      id: 'vibey.showLanes',
      title: 'Show running lanes',
      group: 'Lanes',
      icon: 'pulse',
      slash: 'lanes',
      description: 'Every lane running on this computer, live, and the tasks waiting their turn.',
      example: '/lanes',
    },
    {
      id: 'vibey.openLane',
      title: 'Watch a lane',
      group: 'Lanes',
      icon: 'eye',
      slash: 'watch',
      usage: '<lane id>',
      description: "Stream one lane's events live, whoever started it.",
      example: '/watch 1a2b3c4d',
    },
    {
      id: 'vibey.startQueue',
      title: 'Start the queue',
      group: 'Lanes',
      icon: 'play-circle',
      slash: 'start',
      usage: '[task id]',
      description: 'Let waiting tasks start again; with a task id, that task goes next.',
      example: '/start',
    },
    {
      id: 'vibey.stopAll',
      title: 'Stop all lanes',
      group: 'Lanes',
      icon: 'stop-circle',
      slash: 'stop-all',
      description: 'Hold the queue and wind down every running lane, gracefully, one by one.',
      example: '/stop-all',
    },
    {
      id: 'vibey.refresh',
      title: 'Refresh',
      group: 'Projects & gates',
      icon: 'refresh',
      slash: 'refresh',
      description: 'Read the model, projects, gates and lanes again now.',
      example: '/refresh',
    },
    {
      id: 'vibey.showProjects',
      title: 'Show vibey projects',
      group: 'Projects & gates',
      icon: 'project',
      slash: 'projects',
      description: 'Every vibey project and the phase it is in.',
      example: '/projects',
      wraps: 'vibey projects --json',
    },
    {
      id: 'vibey.showStatus',
      title: "Show a project's status",
      group: 'Projects & gates',
      icon: 'info',
      slash: 'status',
      usage: '[project id]',
      description: "A project's queue and engines.",
      example: '/status',
      wraps: 'vibey status --json',
    },
    {
      id: 'vibey.showGates',
      title: 'Show parked gates',
      group: 'Projects & gates',
      icon: 'question',
      slash: 'gates',
      description: 'Every question vibey is waiting for a person to answer.',
      example: '/gates',
      wraps: 'vibey gates --json',
    },
    {
      id: 'vibey.answerGate',
      title: 'Answer a parked gate',
      group: 'Projects & gates',
      icon: 'comment',
      slash: 'answer',
      usage: '<gate id> [--verdict V | --choice C | --defaults | --raw JSON | Q=A ...]',
      description: 'Answer a gate; with only its id, a list of the answers it takes.',
      example: '/answer 3f2a9c1e-0b7d-4c55-9a51-2b1f0e8d7c6a --verdict accept',
      wraps: 'vibey answer',
    },
    {
      id: 'vibey.bumpJob',
      title: 'Run a queued job next',
      group: 'Projects & gates',
      icon: 'arrow-up',
      slash: 'bump',
      usage: '<job id>',
      description: "Move a vibey job to the front of its project's queue.",
      example: '/bump 5c1d2e3f-4a5b-6c7d-8e9f-0a1b2c3d4e5f',
      wraps: 'vibey queue bump',
    },
    {
      id: 'vibey.showBudgets',
      title: 'Show budgets',
      group: 'Budgets',
      icon: 'graph',
      slash: 'budget',
      usage: '[list]',
      description: "Every budget, for vibey projects and for this machine's lanes, with what is spent.",
      example: '/budget list',
      wraps: 'vibey budget --all --json',
    },
    {
      id: 'vibey.addBudget',
      title: 'Add a budget',
      group: 'Budgets',
      icon: 'add',
      slash: 'budget add',
      usage: 'scope=run|day|month loop=any|sovereignloop|paidloop [engine=ID] dollars=N turns=N minutes=N',
      description: "Cap what this machine's lanes may spend: dollars, turns or minutes, per run, day or month.",
      example: '/budget add scope=day loop=paidloop dollars=5',
    },
    {
      id: 'vibey.editBudget',
      title: 'Edit a budget',
      group: 'Budgets',
      icon: 'edit',
      slash: 'budget edit',
      usage: '<budget id> dollars=N turns=N minutes=N',
      description: "Change a budget's caps; for a vibey project, its cycle caps.",
      example: '/budget edit 1a2b3c4d dollars=10',
      wraps: 'vibey budget set --by vibey-vscode (for a project)',
    },
    {
      id: 'vibey.removeBudget',
      title: 'Remove a budget',
      group: 'Budgets',
      icon: 'remove',
      slash: 'budget remove',
      usage: '<budget id>',
      description: 'Remove a budget; for a vibey project, clear its caps.',
      example: '/budget remove 1a2b3c4d',
      wraps: 'vibey budget clear --by vibey-vscode (for a project)',
    },
    {
      id: 'vibey.grantBudget',
      title: 'Grant more budget',
      group: 'Budgets',
      icon: 'plus',
      slash: 'budget grant',
      usage: '<gate or budget id> $N | N turns',
      description: 'Raise a used-up budget, or answer a parked budget_exhausted gate with more dollars or turns.',
      example: '/budget grant 3f2a9c1e-0b7d-4c55-9a51-2b1f0e8d7c6a $10',
      wraps: 'vibey answer --raw \'{"max_dollars": N}\'',
    },
    {
      id: 'vibey.startOllama',
      title: 'Start Ollama',
      group: 'Ollama',
      icon: 'play',
      slash: 'start-ollama',
      description: 'Start the Ollama server if it is not running; never a second one.',
      example: '/start-ollama',
      wraps: 'open -a Ollama, ollama serve, or systemctl',
    },
    {
      id: 'vibey.pullModel',
      title: 'Download the model',
      group: 'Ollama',
      icon: 'cloud-download',
      slash: 'pull',
      usage: '[model]',
      description: 'Download a model into Ollama, with progress; gpt-oss:20b is about 14 GB.',
      example: '/pull gpt-oss:20b',
      wraps: 'Ollama POST /api/pull (ollama pull)',
    },
    {
      id: 'vibey.doctor',
      title: 'Check my setup (doctor)',
      group: 'Doctor',
      icon: 'pulse',
      slash: 'doctor',
      description: 'Check every piece: the storm home, git, gptossloop, vibey, Ollama, the model and its window.',
      example: '/doctor',
    },
    {
      id: 'vibey.showMenu',
      title: 'Show every command',
      group: 'Doctor',
      icon: 'sparkle',
      slash: 'help',
      description: 'The menu of every command, grouped.',
      example: '/help',
    },
  ];

  static byId(id: string): CommandSpec | undefined {
    return CommandTable.ALL.find((spec) => spec.id === id);
  }

  static grouped(): readonly (readonly [CommandGroup, readonly CommandSpec[]])[] {
    return CommandTable.GROUPS.map((group) => [group, CommandTable.ALL.filter((spec) => spec.group === group)] as const);
  }
}

export class SlashCommands implements SlashCommandsInterface {
  constructor(private readonly table: readonly CommandSpec[] = CommandTable.ALL) {}

  /** The longest slash name that the input starts with wins: `/budget add` before `/budget`. */
  parse(input: string): SlashParse {
    const text = input.trim();
    if (!text.startsWith('/')) {
      return { kind: 'text', text };
    }
    const words = text.slice(1).split(/\s+/);
    const candidates = this.table
      .filter((spec): spec is CommandSpec & { slash: string } => spec.slash !== undefined)
      .sort((left, right) => right.slash.split(' ').length - left.slash.split(' ').length);
    for (const spec of candidates) {
      const name = spec.slash.split(' ');
      if (name.every((word, index) => (words[index] ?? '').toLowerCase() === word)) {
        const consumed = new RegExp(`^/${name.map(SlashCommands.escape).join('\\s+')}\\s*`, 'i');
        return { kind: 'command', spec, args: text.replace(consumed, '').trim() };
      }
    }
    const name = (words[0] as string).toLowerCase();
    return { kind: 'unknown', name, reply: `Unknown command /${name}. Try /help.` };
  }

  /** The first word of every slash command, once each: what @vibey declares as its commands. */
  firstWords(): readonly string[] {
    return [...new Set(this.table.filter((spec) => spec.slash !== undefined).map((spec) => (spec.slash as string).split(' ')[0] as string))];
  }

  private static escape(word: string): string {
    return word.replace(/[.*+?^${}()|[\]\\-]/g, '\\$&');
  }

  complete(typed: string): readonly CommandSpec[] {
    const partial = typed.replace(/^\//, '').toLowerCase();
    return this.table.filter((spec) => spec.slash !== undefined && spec.slash.startsWith(partial));
  }

  help(): string {
    const lines: string[] = [];
    for (const group of CommandTable.GROUPS) {
      const specs = this.table.filter((spec) => spec.group === group && spec.slash !== undefined);
      if (specs.length === 0) {
        continue;
      }
      lines.push(`${group}:`);
      for (const spec of specs) {
        lines.push(`  /${spec.slash}${spec.usage === undefined ? '' : ` ${spec.usage}`}  ${spec.description}`);
      }
    }
    return lines.join('\n');
  }
}

/** The arguments a few commands take, read the same way everywhere. */
export class SlashArguments implements SlashArgumentsInterface {
  loop(args: string): LoopName | string {
    const word = args.trim().toLowerCase();
    if (word === 'sovereign' || word === 'sovereignloop' || word === 'free' || word === 'local') {
      return 'sovereignloop';
    }
    if (word === 'paid' || word === 'paidloop') {
      return 'paidloop';
    }
    return `Say /loop sovereign or /loop paid, not "${args.trim()}".`;
  }

  effort(args: string): EffortSetting | string {
    const word = args.trim();
    if (word.toLowerCase() === 'auto') {
      return 'auto';
    }
    const upper = word.toUpperCase();
    return Efforts.is(upper) ? upper : `Say /effort auto or one of ${Efforts.ALL.join(', ')}, not "${word}".`;
  }

  words(args: string): readonly string[] {
    const words: string[] = [];
    let current = '';
    let quote: string | undefined;
    let started = false;
    for (let index = 0; index < args.length; index += 1) {
      const character = args.charAt(index);
      if (character === '\\' && index + 1 < args.length) {
        current += args.charAt(index + 1);
        index += 1;
        started = true;
      } else if (quote !== undefined) {
        if (character === quote) {
          quote = undefined;
        } else {
          current += character;
        }
      } else if (character === '"' || character === "'") {
        quote = character;
        started = true;
      } else if (/\s/.test(character)) {
        if (started) {
          words.push(current);
          current = '';
          started = false;
        }
      } else {
        current += character;
        started = true;
      }
    }
    if (started) {
      words.push(current);
    }
    return words;
  }
}
