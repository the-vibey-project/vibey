// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Reads a pairing offer. The hub's pairing routes (ADR-0068, "the pairing change") have not
 * landed, so the QR format here is the client's side of that contract, and the exchange of
 * the code for a device key is refused plainly by `PairingExchange` until they do.
 * Declared by `interfaces/pairing-interface.ts`.
 */
import type { PairingInterface, PairingOffer, PairingParse } from './interfaces/pairing-interface';

export class Pairing implements PairingInterface {
  static readonly SCHEMES: readonly string[] = ['krypton:', 'krypton-nightly:'];
  static readonly CODE = /^\d{6}$/;
  static readonly FINGERPRINT = /^sha256:[0-9a-f]{64}$/i;
  static readonly LOOPBACK: readonly string[] = ['127.0.0.1', 'localhost', '::1', '[::1]'];

  parseQr(text: string): PairingParse {
    let url: URL;
    try {
      url = new URL(text.trim());
    } catch {
      return { ok: false, reason: 'That QR code is not a Krypton pairing code.' };
    }
    const target = `${url.host}${url.pathname}`.replace(/^\/+/, '');
    if (!Pairing.SCHEMES.includes(url.protocol) || target !== 'pair') {
      return { ok: false, reason: 'That QR code is not a Krypton pairing code.' };
    }
    const params = url.searchParams;
    const host = params.get('host') ?? '';
    const port = Number(params.get('port') ?? '');
    const code = this.normaliseCode(params.get('code') ?? '');
    const fingerprint = params.get('fp');
    if (host === '' || /[\s/?#@]/.test(host)) {
      return { ok: false, reason: 'The pairing code names no host.' };
    }
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      return { ok: false, reason: 'The pairing code names no valid port.' };
    }
    if (typeof code !== 'string') {
      return { ok: false, reason: code.error };
    }
    const loopback = Pairing.LOOPBACK.includes(host);
    if (fingerprint === null && !loopback) {
      return { ok: false, reason: 'The pairing code carries no certificate fingerprint, so the hub cannot be trusted.' };
    }
    if (fingerprint !== null && !Pairing.FINGERPRINT.test(fingerprint)) {
      return { ok: false, reason: 'The certificate fingerprint in the pairing code is malformed.' };
    }
    const offer: PairingOffer = {
      host,
      port,
      scheme: loopback && fingerprint === null ? 'http' : 'https',
      fingerprint: fingerprint === null ? null : fingerprint.toLowerCase(),
      code,
      name: params.get('name'),
    };
    return { ok: true, offer };
  }

  normaliseCode(typed: string): string | { readonly error: string } {
    const digits = typed.replace(/[\s-]/g, '');
    return Pairing.CODE.test(digits) ? digits : { error: 'The code is the 6 digits the host shows.' };
  }

  baseUrl(offer: PairingOffer): string {
    const host = offer.host.includes(':') && !offer.host.startsWith('[') ? `[${offer.host}]` : offer.host;
    return `${offer.scheme}://${host}:${offer.port}`;
  }
}

/** Exchanging a code for a device key: refused, honestly, until the hub offers the route. */
export class PairingExchange {
  static readonly NOT_YET =
    'This hub cannot pair devices yet: its pairing routes are still being built. ' +
    'For now, connect with the host token (Settings → Connect with a host token).';

  exchange(_offer: PairingOffer): Promise<never> {
    return Promise.reject(new Error(PairingExchange.NOT_YET));
  }
}
