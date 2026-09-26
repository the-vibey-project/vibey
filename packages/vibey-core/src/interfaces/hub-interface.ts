// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Finding a vibey hub on this network and proving a key to it (ADR-0068, SD-01). */

/** What one address said when it was asked whether a hub answers there. */
export interface HubProbe {
  /** The address asked, normalised: scheme, host and port, no path. */
  readonly url: string;
  /** `/health/live` answered 200. */
  readonly live: boolean;
  /** The OpenAPI `info.version` the hub serves (`1` today), when it said. */
  readonly apiVersion?: string;
  /** The hub's OpenAPI document offers a pairing route: one whose path names `pair`. */
  readonly offersPairing: boolean;
  /** Why it is not a hub, in words a person can act on. */
  readonly problem?: string;
}

/** A key checked against a hub: it proves a principal, or it does not. */
export type HubKeyCheck =
  | { readonly ok: true; readonly projects: number }
  | { readonly ok: false; readonly reason: 'refused' | 'forbidden' | 'unreachable' | 'bad-address'; readonly message: string };

export interface HubDiscoveryInterface {
  /** Where to look first: this computer, then the names given, each on the hub's port. */
  candidates(extraNames: readonly string[], port?: number): readonly string[];
  /** Ask every candidate at once; the answers come back in the order asked. */
  probe(urls: readonly string[]): Promise<readonly HubProbe[]>;
  /** Try a key: `GET /api/v1/projects` with it. Being on the network proves nothing (SD-01). */
  checkKey(url: string, key: string): Promise<HubKeyCheck>;
}
