// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { Presenters } from '../core';
import { Card, Label, Loaded, Notice, Pill, Screen, useHub } from '../ui/kit';

const present = new Presenters();

export function LanesScreen() {
  const { result, reload } = useHub((client) => client.lanes(), 2000);
  return (
    <Screen title="Lanes" subtitle="What is running on the host, refreshed every two seconds." onRefresh={reload}>
      <Loaded result={result}>
        {(lanes) => {
          const rows = present.lanes(lanes, Date.now());
          return rows.length === 0 ? (
            <Label tone="tertiary">No lane has run recently.</Label>
          ) : (
            rows.map((row) => (
              <Card key={row.id} role={row.role} testID={`lane-${row.id}`}>
                <Label strong>{row.label}</Label>
                <Pill role={row.role}>{row.state}</Pill>
                <Label tone="secondary">{`${row.written} · ${row.when}`}</Label>
              </Card>
            ))
          );
        }}
      </Loaded>
      <Notice>Stop, wind down and prompt arrive when the hub offers them to devices.</Notice>
    </Screen>
  );
}
