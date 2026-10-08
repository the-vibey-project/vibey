// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The krypton app's Metro configuration. Expo's Metro reads `metro.config.js`; TypeScript is the
// only authored form (sub-doctrine 9.f), so scripts/typescript_artifacts.py compiles this file
// to it. It is compiled to clients/app/, so `__dirname` below is the app directory.
import path = require('node:path');

interface MetroConfig {
  watchFolders: string[];
  resolver: { extraNodeModules: Record<string, string>; nodeModulesPaths: string[] };
}

const { getDefaultConfig } = require('expo/metro-config') as { getDefaultConfig(projectRoot: string): MetroConfig };

const root = path.resolve(__dirname, '../..');
const config = getDefaultConfig(__dirname);
config.watchFolders = [path.join(root, 'packages/vibey-core/src'), path.join(root, 'design/dist/ts')];
config.resolver.extraNodeModules = { '@vibey/core': path.join(root, 'packages/vibey-core/src') };
config.resolver.nodeModulesPaths = [path.join(__dirname, 'node_modules')];

export = config;
