// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import Constants from 'expo-constants';
import { Link } from 'expo-router';
import { Switch, View } from 'react-native';
import { THEME_MODES } from '@vibey/core';
import { SettingsModel } from '../core';
import { useApp } from '../ui/app-state';
import { Button, Card, Label, Screen } from '../ui/kit';
import { useTheme } from '../ui/theme';

const NAMES = { light: 'Light', dark: 'Dark', system: 'System' } as const;

export function SettingsScreen() {
  const { settings, change } = useApp();
  const { colors } = useTheme();
  const channel = (Constants.expoConfig?.extra as { channel?: string } | undefined)?.channel ?? 'stable';
  return (
    <Screen title="Settings">
      <Card>
        <Label strong>Theme</Label>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          {THEME_MODES.map((mode) => (
            <Button key={mode} label={NAMES[mode]} kind={settings.theme === mode ? 'primary' : 'quiet'} onPress={() => change({ type: 'theme', theme: mode })} />
          ))}
        </View>
      </Card>
      <Card>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Label strong>Sounds</Label>
          <Switch accessibilityLabel="Sounds" value={settings.sounds} onValueChange={(on) => change({ type: 'sounds', on })} trackColor={{ true: colors.accent.default }} />
        </View>
      </Card>
      <Card>
        <Label strong>Notifications</Label>
        {SettingsModel.CLASSES.map((which) => (
          <View key={which} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <Label tone="secondary">{SettingsModel.LABELS[which]}</Label>
            <Switch accessibilityLabel={SettingsModel.LABELS[which]} value={settings.notifications[which]} onValueChange={(on) => change({ type: 'notification', which, on })} trackColor={{ true: colors.accent.default }} />
          </View>
        ))}
      </Card>
      <Card>
        <Link href="/budgets"><Label>Budgets →</Label></Link>
        <Link href="/devices"><Label>Devices →</Label></Link>
        <Link href="/doctor"><Label>Doctor →</Label></Link>
      </Card>
      <Label tone="tertiary">{`Channel: ${channel === 'nightly' ? 'Krypton Nightly (from develop)' : 'Krypton (stable, from main)'}`}</Label>
    </Screen>
  );
}
