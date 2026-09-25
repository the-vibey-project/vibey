// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { View } from 'react-native';
import { DevicePolicy, Presenters } from '../core';
import { Card, Label, Loaded, Notice, Screen, useHub } from '../ui/kit';
import { roleColour, useTheme } from '../ui/theme';

const present = new Presenters();

export function BudgetsScreen() {
  const { colors } = useTheme();
  const { result, reload } = useHub((client) => client.budgets(), 10000);
  const refusal = new DevicePolicy().decide('set-cap');
  return (
    <Screen title="Budgets" subtitle="Spend this cycle, against each project's caps." onRefresh={reload}>
      <Loaded result={result}>
        {(budgets) =>
          present.budgets(budgets).map((row) => (
            <Card key={row.projectId} role={row.role}>
              <Label strong>{row.name}</Label>
              <Label tone="secondary">{row.dollars}</Label>
              <Label tone="secondary">{row.turns}</Label>
              {row.fraction !== null ? (
                <View style={{ height: 6, borderRadius: 3, backgroundColor: colors.bg.raised }}>
                  <View style={{ height: 6, borderRadius: 3, width: `${Math.round(row.fraction * 100)}%`, backgroundColor: roleColour(colors, row.role) }} />
                </View>
              ) : null}
            </Card>
          ))
        }
      </Loaded>
      <Notice>{refusal.allowed ? '' : refusal.reason}</Notice>
    </Screen>
  );
}
