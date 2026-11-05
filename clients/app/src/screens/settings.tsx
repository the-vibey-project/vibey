// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Settings screen matching the frontier AI mobile application:
 * User account header with Pro badge, Upgrade card, Profile/Billing/Usage navigation,
 * Capabilities/Claude Code/Connectors/Permissions items, Sounds/Notifications settings,
 * and a 3-card visual Color Mode selector (Light, Dark, System).
 */
import Constants from 'expo-constants';
import { Link, router } from 'expo-router';
import { useState } from 'react';
import {
  Platform,
  Pressable,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import { THEME_MODES } from '@vibey/core';
import type { ThemeMode } from '@vibey/core';
import { SettingsModel } from '../core';
import { useApp } from '../ui/app-state';
import { Button, Card, Label, Screen } from '../ui/kit';
import { useTheme } from '../ui/theme';

export function SettingsScreen() {
  const { settings, change } = useApp();
  const { colors } = useTheme();
  const channel = (Constants.expoConfig?.extra as { channel?: string } | undefined)?.channel ?? 'stable';
  const [notificationsExpanded, setNotificationsExpanded] = useState(false);

  return (
    <Screen title="Settings">
      {/* Top Header Bar */}
      <View style={styles.topBar}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Menu"
          style={styles.headerIconButton}
          onPress={() => {}}
        >
          <Text style={[styles.headerMenuIcon, { color: colors.text.primary }]}>☰</Text>
        </Pressable>
        <Text style={[styles.screenHeaderTitle, { color: colors.text.primary }]}>Settings</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Settings info"
          style={styles.headerIconButton}
        >
          <Text style={[styles.headerInfoIcon, { color: colors.text.tertiary }]}>ⓘ</Text>
        </Pressable>
      </View>

      {/* Account Header with Pro Badge */}
      <View
        style={[
          styles.accountCard,
          { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
        ]}
      >
        <Text style={[styles.accountEmail, { color: colors.text.primary }]}>
          adam@matthewsteinberger.com
        </Text>
        <View style={[styles.proBadge, { backgroundColor: colors.bg.canvas, borderColor: colors.border.strong }]}>
          <Text style={[styles.proBadgeText, { color: colors.text.primary }]}>Pro</Text>
          <Text style={[styles.proBadgeChevron, { color: colors.text.tertiary }]}>▾</Text>
        </View>
      </View>

      {/* Upgrade Banner Card */}
      <View
        style={[
          styles.upgradeCard,
          { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
        ]}
      >
        <Text style={[styles.upgradeTitle, { color: colors.text.primary }]}>
          Want more krypton?
        </Text>
        <Text style={[styles.upgradeSubtitle, { color: colors.text.secondary }]}>
          Upgrade for more usage and capabilities.
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Upgrade"
          style={[styles.upgradeButton, { backgroundColor: colors.bg.canvas, borderColor: colors.border.strong }]}
          onPress={() => {}}
        >
          <Text style={[styles.upgradeButtonText, { color: colors.text.primary }]}>Upgrade</Text>
        </Pressable>
      </View>

      {/* Group 1: Profile, Billing, Usage */}
      <View
        style={[
          styles.groupList,
          { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
        ]}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Profile"
          style={styles.listRow}
          onPress={() => {}}
        >
          <View style={styles.listRowLeft}>
            <Text style={styles.listIcon}>👤</Text>
            <Text style={[styles.listLabel, { color: colors.text.primary }]}>Profile</Text>
          </View>
          <Text style={[styles.chevron, { color: colors.text.tertiary }]}>›</Text>
        </Pressable>

        <View style={[styles.rowDivider, { backgroundColor: colors.border.subtle }]} />

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Billing"
          style={styles.listRow}
          onPress={() => {}}
        >
          <View style={styles.listRowLeft}>
            <Text style={styles.listIcon}>💳</Text>
            <Text style={[styles.listLabel, { color: colors.text.primary }]}>Billing</Text>
          </View>
          <Text style={[styles.chevron, { color: colors.text.tertiary }]}>›</Text>
        </Pressable>

        <View style={[styles.rowDivider, { backgroundColor: colors.border.subtle }]} />

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Usage"
          style={styles.listRow}
          onPress={() => router.push('/usage')}
        >
          <View style={styles.listRowLeft}>
            <Text style={styles.listIcon}>⏱</Text>
            <Text style={[styles.listLabel, { color: colors.text.primary }]}>Usage</Text>
          </View>
          <Text style={[styles.chevron, { color: colors.text.tertiary }]}>›</Text>
        </Pressable>
      </View>

      {/* Group 2: Capabilities, Claude Code / vibey core, Connectors, Permissions */}
      <View
        style={[
          styles.groupList,
          { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
        ]}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Capabilities"
          style={styles.listRow}
          onPress={() => {}}
        >
          <View style={styles.listRowLeft}>
            <Text style={styles.listIcon}>⚙️</Text>
            <View>
              <Text style={[styles.listLabel, { color: colors.text.primary }]}>Capabilities</Text>
              <Text style={[styles.listSubtitle, { color: colors.text.secondary }]}>4 enabled</Text>
            </View>
          </View>
          <Text style={[styles.chevron, { color: colors.text.tertiary }]}>›</Text>
        </Pressable>

        <View style={[styles.rowDivider, { backgroundColor: colors.border.subtle }]} />

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Claude Code"
          style={styles.listRow}
          onPress={() => {}}
        >
          <View style={styles.listRowLeft}>
            <Text style={styles.listIcon}>💻</Text>
            <Text style={[styles.listLabel, { color: colors.text.primary }]}>Claude Code</Text>
          </View>
          <Text style={[styles.chevron, { color: colors.text.tertiary }]}>›</Text>
        </Pressable>

        <View style={[styles.rowDivider, { backgroundColor: colors.border.subtle }]} />

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Connectors"
          style={styles.listRow}
          onPress={() => {}}
        >
          <View style={styles.listRowLeft}>
            <Text style={styles.listIcon}>🔌</Text>
            <View>
              <Text style={[styles.listLabel, { color: colors.text.primary }]}>Connectors</Text>
              <Text style={[styles.listSubtitle, { color: colors.text.secondary }]}>93 connected</Text>
            </View>
          </View>
          <Text style={[styles.chevron, { color: colors.text.tertiary }]}>›</Text>
        </Pressable>

        <View style={[styles.rowDivider, { backgroundColor: colors.border.subtle }]} />

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Permissions"
          style={styles.listRow}
          onPress={() => {}}
        >
          <View style={styles.listRowLeft}>
            <Text style={styles.listIcon}>🤖</Text>
            <View>
              <Text style={[styles.listLabel, { color: colors.text.primary }]}>Permissions</Text>
              <Text style={[styles.listSubtitle, { color: colors.text.secondary }]}>3 enabled</Text>
            </View>
          </View>
          <Text style={[styles.chevron, { color: colors.text.tertiary }]}>›</Text>
        </Pressable>
      </View>

      {/* Sounds Switch Row */}
      <Card>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Label strong>Sounds</Label>
          <Switch
            accessibilityLabel="Sounds"
            value={settings.sounds}
            onValueChange={(on) => change({ type: 'sounds', on })}
            trackColor={{ true: colors.accent.default }}
          />
        </View>
      </Card>

      {/* Notifications Row */}
      <Card>
        <Label strong>Notifications</Label>
        {SettingsModel.CLASSES.map((which) => (
          <View
            key={which}
            style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}
          >
            <Label tone="secondary">{SettingsModel.LABELS[which]}</Label>
            <Switch
              accessibilityLabel={SettingsModel.LABELS[which]}
              value={settings.notifications[which]}
              onValueChange={(on) => change({ type: 'notification', which, on })}
              trackColor={{ true: colors.accent.default }}
            />
          </View>
        ))}
      </Card>

      {/* Visual Color Mode Section */}
      <View style={styles.colorModeSection}>
        <View style={styles.colorModeHeader}>
          <Text style={styles.colorModeIcon}>🌙</Text>
          <Text style={[styles.colorModeTitle, { color: colors.text.primary }]}>Color mode</Text>
        </View>

        <View style={styles.colorModeCardsRow}>
          {/* Light Card */}
          <View style={styles.colorCardWrapper}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Light theme"
              style={[
                styles.colorCard,
                styles.lightPreviewCard,
                settings.theme === 'light' && {
                  borderColor: colors.accent.default,
                  borderWidth: 2,
                },
              ]}
              onPress={() => change({ type: 'theme', theme: 'light' })}
            >
              <View style={styles.lightPreviewContent}>
                <View style={styles.previewLineDark1} />
                <View style={styles.previewLineDark2} />
              </View>
              <View style={styles.previewDot} />
            </Pressable>
            <Text style={[styles.colorCardLabel, { color: colors.text.primary }]}>Light</Text>
          </View>

          {/* Dark Card */}
          <View style={styles.colorCardWrapper}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Dark theme"
              style={[
                styles.colorCard,
                styles.darkPreviewCard,
                settings.theme === 'dark' && {
                  borderColor: colors.accent.default,
                  borderWidth: 2,
                },
              ]}
              onPress={() => change({ type: 'theme', theme: 'dark' })}
            >
              <View style={styles.darkPreviewContent}>
                <View style={styles.previewLineLight1} />
                <View style={styles.previewLineLight2} />
              </View>
              <View style={styles.previewDot} />
            </Pressable>
            <Text style={[styles.colorCardLabel, { color: colors.text.primary }]}>Dark</Text>
          </View>

          {/* System Card */}
          <View style={styles.colorCardWrapper}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="System theme"
              style={[
                styles.colorCard,
                styles.systemPreviewCard,
                settings.theme === 'system' && {
                  borderColor: colors.accent.default,
                  borderWidth: 2,
                },
              ]}
              onPress={() => change({ type: 'theme', theme: 'system' })}
            >
              <View style={styles.systemSplitTopLeft}>
                <View style={styles.previewLineDark1} />
                <View style={styles.previewLineDark2} />
              </View>
              <View style={styles.systemSplitBottomRight}>
                <View style={styles.previewDot} />
              </View>
            </Pressable>
            <Text style={[styles.colorCardLabel, { color: colors.text.primary }]}>System</Text>
          </View>
        </View>
      </View>

      {/* Navigation Links */}
      <Card>
        <Link href="/budgets"><Label>Budgets →</Label></Link>
        <Link href="/devices"><Label>Devices →</Label></Link>
        <Link href="/doctor"><Label>Doctor →</Label></Link>
        <Link href="/workflows"><Label>Run on GitHub →</Label></Link>
      </Card>

      <Label tone="tertiary">
        {`Channel: ${channel === 'nightly' ? 'krypton nightly (from develop)' : 'krypton (stable, from main)'}`}
      </Label>
    </Screen>
  );
}

const styles = StyleSheet.create({
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  headerIconButton: {
    padding: 8,
  },
  headerMenuIcon: {
    fontSize: 22,
    fontWeight: '400',
  },
  screenHeaderTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  headerInfoIcon: {
    fontSize: 18,
  },
  accountCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
  },
  accountEmail: {
    fontSize: 15,
    fontWeight: '600',
  },
  proBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
  },
  proBadgeText: {
    fontSize: 13,
    fontWeight: '600',
  },
  proBadgeChevron: {
    fontSize: 11,
  },
  upgradeCard: {
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    gap: 6,
  },
  upgradeTitle: {
    fontSize: 17,
    fontWeight: '700',
  },
  upgradeSubtitle: {
    fontSize: 14,
    lineHeight: 19,
  },
  upgradeButton: {
    alignSelf: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1,
    marginTop: 6,
  },
  upgradeButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  groupList: {
    borderRadius: 16,
    borderWidth: 1,
    overflow: 'hidden',
  },
  listRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  listRowLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  listIcon: {
    fontSize: 18,
  },
  listLabel: {
    fontSize: 15,
    fontWeight: '500',
  },
  listSubtitle: {
    fontSize: 13,
    marginTop: 1,
  },
  chevron: {
    fontSize: 18,
    fontWeight: '300',
  },
  rowDivider: {
    height: 1,
    marginLeft: 46,
  },
  colorModeSection: {
    gap: 12,
    marginVertical: 4,
  },
  colorModeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  colorModeIcon: {
    fontSize: 16,
  },
  colorModeTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  colorModeCardsRow: {
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  colorCardWrapper: {
    flex: 1,
    alignItems: 'center',
    gap: 6,
  },
  colorCard: {
    width: '100%',
    height: 72,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#383842',
    padding: 10,
    position: 'relative',
    overflow: 'hidden',
    justifyContent: 'space-between',
  },
  colorCardLabel: {
    fontSize: 13,
    fontWeight: '500',
  },
  lightPreviewCard: {
    backgroundColor: '#ffffff',
  },
  darkPreviewCard: {
    backgroundColor: '#1b1c22',
  },
  systemPreviewCard: {
    backgroundColor: '#1b1c22',
    position: 'relative',
  },
  lightPreviewContent: {
    gap: 4,
  },
  darkPreviewContent: {
    gap: 4,
  },
  previewLineDark1: {
    width: 32,
    height: 3,
    borderRadius: 1.5,
    backgroundColor: '#9ca3af',
  },
  previewLineDark2: {
    width: 20,
    height: 3,
    borderRadius: 1.5,
    backgroundColor: '#cbd5e1',
  },
  previewLineLight1: {
    width: 32,
    height: 3,
    borderRadius: 1.5,
    backgroundColor: '#64748b',
  },
  previewLineLight2: {
    width: 20,
    height: 3,
    borderRadius: 1.5,
    backgroundColor: '#475569',
  },
  previewDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#d97706',
    alignSelf: 'flex-end',
  },
  systemSplitTopLeft: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    backgroundColor: '#ffffff',
    padding: 10,
    // Emulate diagonal split using clip/overlay or border trick
    transform: [{ rotate: '-25deg' }, { scale: 1.5 }],
    top: -24,
    left: -24,
  },
  systemSplitBottomRight: {
    position: 'absolute',
    bottom: 8,
    right: 8,
  },
});
