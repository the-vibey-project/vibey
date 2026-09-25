// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Krypton's Expo config. `APP_VARIANT=nightly` builds "Krypton Nightly" (from `develop`), which
 * installs beside the stable "Krypton" (from `main`); with no variant it is always stable.
 * Icons come from the design system's generated set (ADR-0066), never a copy.
 */
import type { ConfigContext, ExpoConfig } from 'expo/config';
// The same file `AppIdentities` reads; a config file cannot import the TypeScript class itself.
import IDENTITIES from './src/core/identities.json';

/** Nightly only when asked for by name, as `AppIdentities.channel` decides; stable otherwise. */
export function identityFor(variant: string | undefined): (typeof IDENTITIES)['stable'] {
  return variant?.trim().toLowerCase() === 'nightly' ? IDENTITIES.nightly : IDENTITIES.stable;
}

const identity = identityFor(process.env.APP_VARIANT);
const ICONS = '../../design/dist/icons';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: identity.name,
  slug: identity.slug,
  scheme: identity.scheme,
  version: '0.1.0',
  orientation: 'default',
  icon: `${ICONS}/ios/AppIcon-1024.png`,
  // Light, Dark or System is the person's choice in Settings; System follows the OS live.
  userInterfaceStyle: 'automatic',
  backgroundColor: '#080b14',
  ios: {
    bundleIdentifier: identity.iosBundleIdentifier,
    supportsTablet: true,
    infoPlist: {
      NSLocalNetworkUsageDescription:
        'Krypton looks for the vibey hub on your Wi-Fi or Ethernet network so you can pair with it.',
      NSBonjourServices: ['_vibey._tcp'],
      NSCameraUsageDescription: 'Krypton scans the pairing QR code your vibey hub shows.',
      NSFaceIDUsageDescription: 'Krypton asks for Face ID before you answer a gate that spends money.',
    },
  },
  android: {
    package: identity.androidPackage,
    adaptiveIcon: {
      foregroundImage: `${ICONS}/android/ic_launcher_foreground.png`,
      backgroundImage: `${ICONS}/android/ic_launcher_background.png`,
    },
    // Multicast lets the app hear the hub's mDNS advert (_vibey._tcp) on the local network.
    permissions: [
      'android.permission.INTERNET',
      'android.permission.ACCESS_NETWORK_STATE',
      'android.permission.ACCESS_WIFI_STATE',
      'android.permission.CHANGE_WIFI_MULTICAST_STATE',
      'android.permission.CAMERA',
      'android.permission.USE_BIOMETRIC',
    ],
  },
  web: {
    favicon: `${ICONS}/web/favicon-32.png`,
    output: 'single',
    bundler: 'metro',
  },
  plugins: [
    'expo-router',
    'expo-secure-store',
    ['expo-camera', { cameraPermission: 'Krypton scans the pairing QR code your vibey hub shows.' }],
    ['expo-local-authentication', { faceIDPermission: 'Krypton asks for Face ID before you answer a gate that spends money.' }],
  ],
  experiments: { typedRoutes: true },
  updates: { requestHeaders: { 'expo-channel-name': identity.updateChannel } },
  extra: { channel: identity.channel },
});
