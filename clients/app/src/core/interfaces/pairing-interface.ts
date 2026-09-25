// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Pairing a device with a hub, once: by the QR code the host shows or by its 6-digit code.
 * Being on the same network proves nothing (SD-01); the code does, for two minutes.
 */

/** What the host's QR code carries: `krypton://pair?host=…&port=…&fp=sha256:…&code=123456`. */
export interface PairingOffer {
  readonly host: string;
  readonly port: number;
  /** `https`, unless the host is this device's own loopback. */
  readonly scheme: 'http' | 'https';
  /** The hub certificate's SHA-256 fingerprint, trusted on first use because the QR carried it. */
  readonly fingerprint: string | null;
  readonly code: string;
  /** The host's own name for itself, shown while pairing. */
  readonly name: string | null;
}

export type PairingParse = { readonly ok: true; readonly offer: PairingOffer } | { readonly ok: false; readonly reason: string };

export interface PairingInterface {
  /** A scanned QR code's text, checked. */
  parseQr(text: string): PairingParse;
  /** A typed code, with spaces and dashes taken out; an error message when it is not 6 digits. */
  normaliseCode(typed: string): string | { readonly error: string };
  /** `https://host:port`. */
  baseUrl(offer: PairingOffer): string;
}
