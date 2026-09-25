// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The screen table: one place the tab bar, the router and the parity check all read. Declared by `interfaces/screens-interface.ts`. */
import type { ParityFeature, ScreenSpec, ScreensInterface } from './interfaces/screens-interface';

export class Screens implements ScreensInterface {
  static readonly FEATURES: readonly ParityFeature[] = [
    'projects-and-phases',
    'gates',
    'lanes-live',
    'loop-engine-effort',
    'budgets-and-spend',
    'doctor',
    'command-palette',
    'notifications',
    'devices-and-pairing',
    'themes',
    'onboarding',
  ];

  readonly all: readonly ScreenSpec[] = [
    { route: '/', title: 'Home', icon: 'home', tab: true, features: ['projects-and-phases'], gaps: [] },
    { route: '/gates', title: 'Gates', icon: 'gate', tab: true, features: ['gates'], gaps: [] },
    {
      route: '/lanes',
      title: 'Lanes',
      icon: 'lanes',
      tab: true,
      features: ['lanes-live'],
      gaps: ['Stop, wind down and prompt wait for the hub routes; the list refreshes rather than streams.'],
    },
    {
      route: '/effort',
      title: 'Loops & Effort',
      icon: 'effort',
      tab: true,
      features: ['loop-engine-effort', 'command-palette'],
      gaps: ['The choice is shown and checked here; the hub has no route to start a run yet.'],
    },
    { route: '/settings', title: 'Settings', icon: 'settings', tab: true, features: ['themes', 'notifications'], gaps: [] },
    { route: '/budgets', title: 'Budgets', icon: 'budget', tab: false, features: ['budgets-and-spend'], gaps: [] },
    {
      route: '/devices',
      title: 'Devices',
      icon: 'device',
      tab: false,
      features: ['devices-and-pairing'],
      gaps: ['Listing and revoking other devices waits for the hub pairing routes.'],
    },
    { route: '/doctor', title: 'Doctor', icon: 'doctor', tab: false, features: ['doctor'], gaps: [] },
    {
      route: '/pair',
      title: 'Welcome',
      icon: 'atom',
      tab: false,
      features: ['onboarding', 'devices-and-pairing'],
      gaps: ['Pairing by QR or code waits for the hub pairing routes; the host token connects today.'],
    },
  ];

  readonly tabs: readonly ScreenSpec[] = this.all.filter((screen) => screen.tab);

  missing(): readonly ParityFeature[] {
    const carried = new Set(this.all.flatMap((screen) => screen.features));
    return Screens.FEATURES.filter((feature) => !carried.has(feature));
  }
}
