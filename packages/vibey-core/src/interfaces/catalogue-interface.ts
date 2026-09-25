// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * `vibey loops --json`: the two loops, their engines, what each effort runs, and the
 * escalation ladder (contract: vibey-loops.md). The extension reads this and hard-codes no
 * engine's facts of its own.
 */

export type Effort = 'TRIVIAL' | 'LOW' | 'STANDARD' | 'HIGH' | 'MAX';
export type LoopName = 'sovereignloop' | 'paidloop';

/**
 * How an engine writes its events: a top-level `type` (codexloop, gptossloop, qwenloop), `event_type`
 * with a `payload` (claudeloop, agyloop), or `event_type` beside flat fields (no engine
 * today; the deleted opencodeloop wrote it, and `vibey loops` still names the shape).
 */
export type EventEnvelope = 'type' | 'event_type+payload' | 'event_type';

export interface EngineEffort {
  readonly effort: Effort;
  readonly argv: readonly string[];
  readonly achieved: Effort;
  readonly model: string | null;
  readonly notes: string;
}

export interface EngineCapabilities {
  readonly images: boolean | null;
  readonly files: boolean | null;
  readonly paste_text: boolean | null;
  readonly paste_images: boolean | null;
  /** "skills-context", "claude-plugins", or null (unknown). */
  readonly plugins: string | null;
  readonly mcp: boolean | null;
  readonly evidence: Readonly<Record<string, string>>;
}

export interface EngineControls {
  readonly stop: readonly string[] | null;
  readonly wind_down: readonly string[] | null;
  readonly prompt: readonly string[] | null;
}

export interface CatalogueEngine {
  readonly engine_id: string;
  readonly binary: string;
  readonly state_dir: string;
  readonly enabled: boolean;
  /** Repealed by the canon (8.b) while its code is still in vibey: listed for transparency, and never run. */
  readonly repealed: boolean;
  readonly switch: string | null;
  /**
   * Whether vibey switches it on unless its switch says otherwise (gptossloop, ADR-0064). A
   * producer from before the key existed switched nothing on by default: false.
   */
  readonly on_by_default: boolean;
  readonly cost_per_mtok_in: number;
  readonly cost_per_mtok_out: number;
  readonly default_model: string | null;
  readonly efforts: readonly EngineEffort[];
  readonly capabilities: EngineCapabilities;
  readonly done_marker: string | null;
  readonly plan_flag: string | null;
  readonly supports_cwd_flag: boolean;
  readonly base_weight: number;
  readonly run: readonly string[];
  readonly controls: EngineControls;
  readonly events: { readonly path: string; readonly envelope: EventEnvelope };
  readonly env: { readonly auth: readonly string[]; readonly passthrough: readonly string[] };
  /** What vibey says about the engine, one line each. */
  readonly notes?: readonly string[];
  /**
   * The flag that sets a turn limit, when this engine takes one. Not part of the JSON: it is
   * derived from the effort projections, which show it wherever an engine has it.
   */
  readonly turns_flag?: string;
}

export interface EffortChoice {
  readonly engine_id: string;
  readonly model: string | null;
  readonly achieved: Effort;
}

export interface CatalogueLoop {
  readonly loop: LoopName;
  readonly tier: 'local' | 'paid';
  readonly default: boolean;
  readonly declared_only: boolean;
  readonly engines: readonly CatalogueEngine[];
  readonly by_effort: Readonly<Partial<Record<Effort, readonly EffortChoice[]>>>;
}

export interface Ladder {
  readonly phase_base: Readonly<Record<string, Effort>>;
  readonly build_attempts: readonly Effort[];
  readonly exhausted_after: number;
  readonly rotates_when_effort_rises: boolean;
}

export interface Catalogue {
  readonly efforts: readonly Effort[];
  readonly default_loop: LoopName;
  readonly paid_default_engine: string;
  readonly ladder: Ladder;
  readonly loops: readonly CatalogueLoop[];
  /** Where it came from: `vibey loops --json`, or the degraded sovereign default. */
  readonly source: 'vibey' | 'degraded';
  /** Why it is degraded, in words a person can act on. */
  readonly notice?: string;
}

export interface CatalogueParserInterface {
  parse(value: unknown): Catalogue;
}

export interface CatalogueSourceInterface {
  /** `vibey loops --json`, or the degraded default with a plain notice when that fails. */
  load(): Promise<Catalogue>;
}

export type EffortSetting = Effort | 'auto';

export interface SelectionRequest {
  readonly loop: LoopName;
  readonly effort: EffortSetting;
  /** `auto`, an engine id, or `engine/model`. */
  readonly engine: string;
  /** The task's base effort, where auto starts. */
  readonly baseEffort: Effort;
  /** 1-based: auto effort climbs the ladder one rung per failed attempt. */
  readonly attempt: number;
  /** The engine the previous attempt used, so a rise in effort rotates away from it. */
  readonly previousEngine?: string;
  /** Models Ollama holds in memory now; a local choice prefers these. */
  readonly resident: readonly string[];
  readonly paidDeclared: boolean;
  /** A task's own turn limit, which wins over everything else. */
  readonly taskMaxTurns?: number;
  /** The vibey.maxTurns setting, the last resort. */
  readonly settingMaxTurns?: number;
}

export interface Selection {
  readonly loop: LoopName;
  readonly tier: 'local' | 'paid';
  readonly effort: Effort;
  readonly effortSource: 'chosen' | 'auto' | 'model';
  readonly engine: CatalogueEngine;
  readonly model: string | null;
  /** The effort argv with the turn budget applied once. */
  readonly argv: readonly string[];
  readonly maxTurns?: number;
  readonly maxTurnsSource: 'task' | 'effort' | 'setting' | 'none' | 'not supported by this engine';
  /** Why this engine and model: what a person reads in the journal. */
  readonly reason: string;
}

export interface LoopSelectorInterface {
  select(request: SelectionRequest): Selection;
  /** The effort for a 1-based attempt from a base, as vibey's `effort_for_attempt`. */
  effortForAttempt(base: Effort, attempt: number): Effort;
}
