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
 *
 * A notification about a question the phone may answer carries the answers as buttons, so a
 * person can answer without opening the app. Which gates get buttons, and what a button means,
 * is `NotificationPlanner`'s: a gate that spends never has one, and a button is checked again
 * against the gate's kind when it is pressed, so nothing here can answer a spending gate.
 */
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { useEffect, useRef } from 'react';
import { Platform } from 'react-native';
import { NotificationPlanner } from '../core';
import type { HubClient, NotificationSnapshot } from '../core';
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

function gateOptions(snapshot: NotificationSnapshot, gateId: string | undefined): readonly string[] {
  return snapshot.gates.find((gate) => gate.id === gateId)?.options ?? [];
}

async function say(identifier: string, title: string, body: string, route: '/gates' | '/'): Promise<void> {
  await Notifications.scheduleNotificationAsync({ identifier, content: { title, body, data: { route } }, trigger: null });
}

/** A button was pressed on a gate's notification: send that answer, and say how it went. Never silently. */
async function answerFromNotification(client: HubClient, response: Notifications.NotificationResponse): Promise<void> {
  const data = response.notification.request.content.data ?? {};
  const { gateId, gateKind, options } = data as { gateId?: unknown; gateKind?: unknown; options?: unknown };
  if (typeof gateId !== 'string' || typeof gateKind !== 'string' || !Array.isArray(options)) return;
  const answer = planner.answerFor(
    gateKind,
    options.filter((option): option is string => typeof option === 'string'),
    response.actionIdentifier,
  );
  if (answer === undefined) return;
  try {
    await say(`answered-${gateId}`, 'Answered', await client.answer(gateId, answer), '/gates');
  } catch (error) {
    // The hub is away or refused: the question is still waiting, so say that and open Gates on a tap.
    await say(`answered-${gateId}`, 'Your answer was not sent', `${error instanceof Error ? error.message : String(error)} Open krypton to answer.`, '/gates');
  }
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
      if (response.actionIdentifier === Notifications.DEFAULT_ACTION_IDENTIFIER) {
        router.push(response.notification.request.content.data?.route === '/gates' ? '/gates' : '/');
        return;
      }
      void answerFromNotification(client, response);
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
          const category = notification.actions.length === 0 ? undefined : planner.categoryFor(notification.actions);
          if (category !== undefined) {
            // `isAuthenticationRequired`: on iOS a button answers only once the phone is unlocked.
            await Notifications.setNotificationCategoryAsync(
              category,
              notification.actions.map((action) => ({
                identifier: action.id,
                buttonTitle: action.title,
                options: { opensAppToForeground: false, isAuthenticationRequired: true },
              })),
            );
          }
          await Notifications.scheduleNotificationAsync({
            identifier: notification.id,
            content: {
              title: notification.title,
              body: notification.body,
              data: { route: notification.route, gateId: notification.gateId, gateKind: notification.gateKind, options: gateOptions(after, notification.gateId) },
              categoryIdentifier: category,
              sound: settings.sounds,
            },
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
