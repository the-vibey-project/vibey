// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Usage screen matching the frontier AI mobile application:
 * Session usage progress, weekly limits progress, limit resets status, usage credits toggle and balance.
 */
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Switch, Text, View } from 'react-native';
import { Button, Card, Label, Screen } from '../ui/kit';
import { useTheme } from '../ui/theme';

export function UsageScreen() {
  const { colors } = useTheme();
  const [usageCreditsEnabled, setUsageCreditsEnabled] = useState(true);

  return (
    <Screen title="Usage">
      {/* Top Header with Back Button and Info Icon */}
      <View style={styles.topBar}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back"
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Text style={[styles.backIcon, { color: colors.text.primary }]}>←</Text>
        </Pressable>
        <Text style={[styles.headerTitle, { color: colors.text.primary }]}>Usage</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Usage info"
          style={styles.infoButton}
        >
          <Text style={[styles.infoIcon, { color: colors.text.tertiary }]}>ⓘ</Text>
        </Pressable>
      </View>

      {/* Notice Banner */}
      <View
        style={[
          styles.noticeBanner,
          { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
        ]}
      >
        <Text style={[styles.noticeText, { color: colors.text.primary }]}>
          Heads up. At this pace you'll run out this morning, before Tuesday's reset.
        </Text>
      </View>

      {/* Current Session Card */}
      <Card testID="usage-current-session">
        <View style={styles.cardHeaderRow}>
          <Label strong>Current session</Label>
          <Text style={[styles.statValue, { color: colors.text.secondary }]}>0% used</Text>
        </View>
        <View style={[styles.progressBarTrack, { backgroundColor: colors.bg.canvas }]}>
          <View
            style={[
              styles.progressBarFill,
              { width: '0%', backgroundColor: colors.accent.default },
            ]}
          />
        </View>
        <Label tone="secondary">Starts with your first message</Label>
      </Card>

      {/* Weekly Limits Section */}
      <Label strong>Weekly limits</Label>
      <Card testID="usage-weekly-limits">
        <View style={styles.cardHeaderRow}>
          <Label strong>All models</Label>
          <Text style={[styles.statValue, { color: colors.status.danger }]}>96% used</Text>
        </View>
        <View style={[styles.progressBarTrack, { backgroundColor: colors.bg.canvas }]}>
          <View
            style={[
              styles.progressBarFill,
              { width: '96%', backgroundColor: colors.status.danger },
            ]}
          />
        </View>
        <Label tone="secondary">Resets Tue 02:00</Label>
      </Card>

      {/* Limit Resets Section */}
      <Label strong>Limit resets</Label>
      <Card testID="usage-limit-resets">
        <Label strong>No resets right now</Label>
        <Label tone="secondary">When you get one, it shows up here with its expiry date.</Label>
      </Card>

      {/* Credits Section */}
      <Label strong>Credits</Label>
      <Card testID="usage-credits">
        <View style={styles.cardHeaderRow}>
          <Label strong>Usage credits</Label>
          <Switch
            accessibilityLabel="Usage credits switch"
            value={usageCreditsEnabled}
            onValueChange={setUsageCreditsEnabled}
            trackColor={{ true: colors.accent.default, false: colors.border.subtle }}
          />
        </View>
        <Label tone="secondary">
          Turn on usage credits to keep using krypton if you hit a plan limit.{' '}
          <Text style={{ color: colors.accent.default }}>Learn more.</Text>
        </Label>
        <View style={[styles.divider, { backgroundColor: colors.border.subtle }]} />
        <View style={styles.cardHeaderRow}>
          <Label strong>Current balance</Label>
          <Text style={[styles.statValue, { color: colors.text.secondary }]}>0 credits</Text>
        </View>
      </Card>

      <Text style={[styles.footnote, { color: colors.text.tertiary }]}>
        Usage credits cover you when you hit your plan limits.{' '}
        <Text style={{ color: colors.accent.default }}>Learn more</Text>
      </Text>

      <Button label="Buy usage credits" kind="quiet" onPress={() => {}} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
    marginBottom: 4,
  },
  backButton: {
    padding: 8,
  },
  backIcon: {
    fontSize: 22,
    fontWeight: '400',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  infoButton: {
    padding: 8,
  },
  infoIcon: {
    fontSize: 18,
  },
  noticeBanner: {
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    marginBottom: 4,
  },
  noticeText: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '500',
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statValue: {
    fontSize: 15,
    fontWeight: '500',
  },
  progressBarTrack: {
    height: 6,
    borderRadius: 3,
    marginVertical: 10,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  divider: {
    height: 1,
    marginVertical: 12,
  },
  footnote: {
    fontSize: 13,
    lineHeight: 18,
    marginVertical: 4,
  },
});
