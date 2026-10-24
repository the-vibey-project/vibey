// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Tells a person when a project needs them or finishes, with the phone's own notifications.
 * Everything about *what* is worth a notification is `NotificationPlanner`'s (tested to 100%);
 * this only looks at the hub every few seconds, asks the planner, and shows what it returns
 * through expo-notifications, honoring the switches in Settings.
 *
 * It looks while the app is open or recently in the background. A phone that has closed the app
 * hears nothing: that needs the hub to push through Apple's and Google's services, which it
 * does not yet do (see the issue linked from Settings).
 */
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { useEffect, useRef } from 'react';
import { Platform } from 'react-native';
import { NotificationPlanner } from '../core';
import type { NotificationSnapshot } from '../core';
import { useApp } from './app-state';

const planner = new NotificationPlanner();

/** How often the hub is looked at. A notification is not worth a faster poll than a person would refresh. */
export const NOTIFICATION_POLL_MS = 15_000;

/** The OS's permission to notify, asked once, the first time there is something worth saying. */
export async function allowed(): Promise<boolean> {
  const current = await Notifications.getPermissionsAsync();
  if (current.granted) return true;
  if (!current.canAskAgain) return false;
  return (await Notifications.requestPermissionsAsync()).granted;
}

export function GateNotifications() {
  const { client, settings } = useApp();
  const last = useRef<NotificationSnapshot | undefined>(undefined);

  useEffect(() => {
    if (Platform.OS === 'web' || client === null) {
      last.current = undefined;
      return undefined;
    }
    Notifications.setNotificationHandler({
      handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: settings.sounds, shouldSetBadge: false }),
    });
    const tapped = Notifications.addNotificationResponseReceivedListener((response) => {
      router.push(response.notification.request.content.data?.route === '/gates' ? '/gates' : '/');
    });
    let stopped = false;
    const look = async () => {
      try {
        const [projects, gates] = await Promise.all([client.projects(), client.gates()]);
        const after = planner.snapshot(projects, gates);
        const due = planner.plan(last.current, after, settings.notifications);
        last.current = after;
        if (stopped || due.length === 0 || !(await allowed())) return;
        for (const notification of due) {
          await Notifications.scheduleNotificationAsync({
            identifier: notification.id,
            content: { title: notification.title, body: notification.body, data: { route: notification.route }, sound: settings.sounds },
            trigger: null,
          });
        }
      } catch {
        // The hub is away or refused: the next look tries again, and the screens say so themselves.
      }
    };
    void look();
    const timer = setInterval(() => void look(), NOTIFICATION_POLL_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
      tapped.remove();
    };
  }, [client, settings.sounds, settings.notifications]);

  return null;
}
