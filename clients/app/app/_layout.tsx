// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { AppStateProvider } from '../src/ui/app-state';
import { useTheme } from '../src/ui/theme';

function Navigator() {
  const { mode, colors } = useTheme();
  return (
    <>
      <StatusBar style={mode === 'dark' ? 'light' : 'dark'} />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg.surface },
          headerTintColor: colors.accent.default,
          headerTitleStyle: { color: colors.text.primary },
          contentStyle: { backgroundColor: colors.bg.canvas },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="pair" options={{ headerShown: false, presentation: 'modal' }} />
        <Stack.Screen name="budgets" options={{ title: 'Budgets' }} />
        <Stack.Screen name="devices" options={{ title: 'Devices' }} />
        <Stack.Screen name="doctor" options={{ title: 'Doctor' }} />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  return (
    <AppStateProvider>
      <Navigator />
    </AppStateProvider>
  );
}
