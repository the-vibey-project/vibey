// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { Redirect, Tabs } from 'expo-router';
import { Text } from 'react-native';
import { Screens } from '../../src/core';
import { useApp } from '../../src/ui/app-state';
import { useTheme } from '../../src/ui/theme';

const GLYPHS: Record<string, string> = { home: '⌂', gate: '◈', lanes: '≋', effort: '⚛', settings: '⚙' };
const FILES: Record<string, string> = { '/': 'index', '/gates': 'gates', '/lanes': 'lanes', '/effort': 'effort', '/settings': 'settings' };

export default function TabsLayout() {
  const { ready, connection } = useApp();
  const { colors } = useTheme();
  if (ready && connection === null) return <Redirect href="/pair" />;
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: { backgroundColor: colors.bg.surface, borderTopColor: colors.border.subtle },
        tabBarActiveTintColor: colors.accent.default,
        tabBarInactiveTintColor: colors.text.tertiary,
      }}
    >
      {new Screens().tabs.map((screen) => (
        <Tabs.Screen
          key={screen.route}
          name={FILES[screen.route] ?? 'index'}
          options={{
            title: screen.title,
            tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>{GLYPHS[screen.icon]}</Text>,
          }}
        />
      ))}
    </Tabs>
  );
}
