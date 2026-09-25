// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The hub, as Krypton on a phone or in a browser reaches it: every route of
 * `docs/reference/hub-api.json` (ADR-0068) that a device may call, and nothing more.
 */
import type { VibeyTransportInterface } from '@vibey/core';

/** What `fetch` gives back, as far as the client reads it. */
export interface FetchResponse {
  readonly status: number;
  text(): Promise<string>;
}

export interface FetchInit {
  readonly method: 'GET' | 'POST';
  readonly headers: Readonly<Record<string, string>>;
  readonly body?: string;
}

/** `globalThis.fetch`, injected so the client stays pure and testable. */
export type FetchLike = (url: string, init: FetchInit) => Promise<FetchResponse>;

/** Where a hub is and who this device is to it. */
export interface HubConnection {
  /** `http://127.0.0.1:8765`, with no trailing slash. */
  readonly baseUrl: string;
  /** The host token, or this device's key once pairing lands. Never logged, never shown. */
  readonly token: string;
}

/** One lane of `GET /api/v1/lanes`. */
export interface HubLane {
  readonly id: string;
  readonly engine: string;
  /** `<worktree> · <engine>`. */
  readonly label: string;
  readonly state: 'running' | 'quiet' | 'finished' | string;
  readonly outcome: string | null;
  /** Bytes written to its events file: the position a reader resumes after (10.g). */
  readonly offset: number;
  /** Seconds since the epoch. */
  readonly last_event_at: number;
}

/** One check of `GET /api/v1/doctor`. */
export interface HubDoctorCheck {
  readonly name: string;
  /** `PASS`, `WARN` or `FAIL`, as `vibey doctor` marks it. */
  readonly mark: string;
  readonly detail: string;
}

export interface HubDoctor {
  /** What the hub says it checked: `vibey doctor` on the host is the full check. */
  readonly scope: string;
  readonly checks: readonly HubDoctorCheck[];
}

/** One job of `GET /api/v1/projects/{id}/queue`. */
export interface HubQueueJob {
  readonly job_id: string;
  readonly kind: string;
  readonly state: string;
  readonly phase: string;
  /** Claim order; null for work that is running or not claimable here. */
  readonly position: number | null;
}

/** Why the hub refused, in words a person can act on. */
export type HubRefusal =
  | 'unreachable'
  | 'unauthenticated'
  | 'forbidden'
  | 'not-found'
  | 'conflict'
  | 'wrong-host'
  | 'invalid'
  | 'too-many'
  | 'unavailable'
  | 'bad-answer'
  | 'not-on-a-device';

/** Every call a Krypton device makes. The CLI-shaped calls come from `VibeyTransportInterface`. */
export interface HubClientInterface extends VibeyTransportInterface {
  readonly connection: HubConnection;
  /** `GET /health/live` and `/health/ready`: needs no credentials. */
  health(): Promise<{ readonly live: boolean; readonly ready: boolean }>;
  lanes(): Promise<readonly HubLane[]>;
  doctor(): Promise<HubDoctor>;
  queue(projectId: string): Promise<readonly HubQueueJob[]>;
}
