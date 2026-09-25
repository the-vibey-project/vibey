// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Colours from the one design-token module (ADR-0066), resolved Light, Dark or System. */
import { resolveTheme, themes } from '@vibey/core';
import type { ResolvedTheme } from '@vibey/core';
import { useColorScheme } from 'react-native';
import type { StatusRole } from '../core';
import { useApp } from './app-state';

export type Palette = (typeof themes)['dark'];

export function useTheme(): { readonly mode: ResolvedTheme; readonly colors: Palette } {
  const system = useColorScheme();
  const { settings } = useApp();
  const mode = resolveTheme(settings.theme, system !== 'light');
  return { mode, colors: themes[mode] as Palette };
}

/** A status role's colour (`color.status.*`); neutral is the tertiary text. */
export function roleColour(colors: Palette, role: StatusRole): string {
  return role === 'neutral' ? colors.text.tertiary : colors.status[role];
}
