// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The few pieces every screen is built from, drawn with the design tokens. */
import { useCallback, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { HubError, HubStatus } from '../core';
import type { HubClient, StatusRole } from '../core';
import { useApp } from './app-state';
import { copyText } from './clipboard';
import { roleColour, useTheme } from './theme';

const radius = 16;

export function Screen(props: { readonly title: string; readonly subtitle?: string; readonly children: ReactNode; readonly onRefresh?: () => void }) {
  const { colors } = useTheme();
  return (
    <ScrollView
      style={{ backgroundColor: colors.bg.canvas }}
      contentContainerStyle={styles.screen}
      refreshControl={props.onRefresh ? <RefreshControl refreshing={false} onRefresh={props.onRefresh} tintColor={colors.accent.default} /> : undefined}
    >
      <Text accessibilityRole="header" style={[styles.title, { color: colors.text.primary }]}>
        {props.title}
      </Text>
      {props.subtitle ? <Text style={[styles.subtitle, { color: colors.text.secondary }]}>{props.subtitle}</Text> : null}
      {props.children}
    </ScrollView>
  );
}

export function Card(props: { readonly children: ReactNode; readonly role?: StatusRole; readonly testID?: string }) {
  const { colors } = useTheme();
  return (
    <View
      testID={props.testID}
      style={[
        styles.card,
        { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
        props.role ? { borderLeftColor: roleColour(colors, props.role), borderLeftWidth: 4 } : null,
      ]}
    >
      {props.children}
    </View>
  );
}

export function Label(props: { readonly children: ReactNode; readonly tone?: 'primary' | 'secondary' | 'tertiary'; readonly strong?: boolean }) {
  const { colors } = useTheme();
  return (
    <Text style={{ color: colors.text[props.tone ?? 'primary'], fontSize: props.strong ? 17 : 15, fontWeight: props.strong ? '600' : '400', marginVertical: 2 }}>
      {props.children}
    </Text>
  );
}

export function Pill(props: { readonly role: StatusRole; readonly children: ReactNode }) {
  const { colors } = useTheme();
  const colour = roleColour(colors, props.role);
  return (
    <View style={[styles.pill, { borderColor: colour }]}>
      <Text style={{ color: colour, fontSize: 12, fontWeight: '600' }}>{props.children}</Text>
    </View>
  );
}

export function Button(props: { readonly label: string; readonly onPress: () => void; readonly kind?: 'primary' | 'quiet' | 'danger'; readonly disabled?: boolean }) {
  const { colors } = useTheme();
  const kind = props.kind ?? 'primary';
  const background = kind === 'primary' ? colors.accent.default : kind === 'danger' ? colors.status.danger : 'transparent';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: props.disabled === true }}
      disabled={props.disabled}
      onPress={props.onPress}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: background, borderColor: colors.accent.default, opacity: props.disabled ? 0.4 : pressed ? 0.8 : 1 },
      ]}
    >
      <Text style={{ color: kind === 'quiet' ? colors.accent.default : colors.text['on-accent'], fontWeight: '600', fontSize: 15 }}>{props.label}</Text>
    </Pressable>
  );
}

export function Notice(props: { readonly children: ReactNode; readonly role?: StatusRole }) {
  const { colors } = useTheme();
  return (
    <View accessibilityRole="alert" style={[styles.notice, { borderColor: roleColour(colors, props.role ?? 'info') }]}>
      <Text style={{ color: colors.text.secondary, fontSize: 14 }}>{props.children}</Text>
    </View>
  );
}

const STATUS = new HubStatus();

/**
 * What a phone says when the hub does not answer: the hub runs on another computer, so the
 * way back is a command to run there (#1186). Nothing here starts or stops a hub.
 */
export function UnreachableCard() {
  const { connection } = useApp();
  const [copied, setCopied] = useState(false);
  const view = STATUS.unreachable(connection?.baseUrl ?? 'the hub');
  return (
    <Card role="danger" testID="hub-unreachable">
      <Label strong>{view.headline}</Label>
      <Label tone="secondary">{view.body}</Label>
      <Label tone="primary">{`On that computer, run:  ${view.command}`}</Label>
      <Button label={view.copyLabel} kind="quiet" onPress={() => void copyText(view.command).then(setCopied)} />
      {copied ? <Label tone="tertiary">Copied.</Label> : null}
      {view.notes.map((note) => (
        <Label key={note} tone="tertiary">{note}</Label>
      ))}
    </Card>
  );
}

/** Reachable or not, the address, and since when: the phone's hub status. */
export function HubStatusCard() {
  const { connection, watch } = useApp();
  if (connection === null) return null;
  const line = STATUS.line(watch, connection.baseUrl, Date.now());
  return (
    <Card role={line.role} testID="hub-status">
      <Label strong>The hub on your computer</Label>
      <Pill role={line.role}>{line.label}</Pill>
      <Label tone="secondary">{line.detail}</Label>
    </Card>
  );
}

export type Load<T> =
  | { readonly state: 'loading' }
  | { readonly state: 'ready'; readonly value: T }
  | { readonly state: 'failed'; readonly message: string; readonly unreachable?: true };

/** Loads from the hub now and every `everyMs` after (the hub has no live feed for devices yet). */
export function useHub<T>(load: (client: HubClient) => Promise<T>, everyMs = 5000): { readonly result: Load<T>; readonly reload: () => void } {
  const { client, recoveries } = useApp();
  const [result, setResult] = useState<Load<T>>({ state: 'loading' });
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((value) => value + 1), []);
  useEffect(() => {
    if (client === null) {
      setResult({ state: 'failed', message: 'Not connected to a hub yet.' });
      return;
    }
    let live = true;
    load(client).then(
      (value) => live && setResult({ state: 'ready', value }),
      (error: unknown) => {
        if (!live) return;
        const unreachable = error instanceof HubError && error.refusal === 'unreachable';
        setResult({ state: 'failed', message: error instanceof Error ? error.message : String(error), ...(unreachable ? { unreachable: true as const } : {}) });
        // A hub that does not answer is watched by the watch, which backs off and reloads this
        // screen when it answers again; this screen only asks again at the slowest pace.
        if (unreachable) {
          if (timer !== undefined) clearTimeout(timer);
          timer = setTimeout(reload, HubStatus.STEADY_MS);
        }
      },
    );
    let timer: ReturnType<typeof setTimeout> | undefined = everyMs > 0 ? setTimeout(reload, everyMs) : undefined;
    return () => {
      live = false;
      if (timer !== undefined) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [client, tick, recoveries]);
  return { result, reload };
}

export function Loaded<T>(props: { readonly result: Load<T>; readonly children: (value: T) => ReactNode }) {
  const { colors } = useTheme();
  if (props.result.state === 'loading') return <ActivityIndicator color={colors.accent.default} />;
  if (props.result.state === 'failed') return props.result.unreachable === true ? <UnreachableCard /> : <Notice role="danger">{props.result.message}</Notice>;
  return <>{props.children(props.result.value)}</>;
}

const styles = StyleSheet.create({
  screen: { padding: 16, gap: 12, maxWidth: 760, width: '100%', alignSelf: 'center' },
  title: { fontSize: 30, fontWeight: '700', letterSpacing: -0.5, marginTop: 8 },
  subtitle: { fontSize: 15, marginBottom: 4 },
  card: { borderRadius: radius, borderWidth: StyleSheet.hairlineWidth, padding: 16, gap: 6 },
  pill: { alignSelf: 'flex-start', borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 2 },
  button: { borderRadius: 12, borderWidth: 1, paddingVertical: 12, paddingHorizontal: 18, alignItems: 'center', marginVertical: 4 },
  notice: { borderLeftWidth: 3, paddingVertical: 8, paddingHorizontal: 12 },
});
