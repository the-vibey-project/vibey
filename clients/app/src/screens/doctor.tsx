// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { Presenters } from '../core';
import { Card, Label, Loaded, Pill, Screen, useHub } from '../ui/kit';

const present = new Presenters();

export function DoctorScreen() {
  const { result, reload } = useHub((client) => client.doctor(), 0);
  return (
    <Screen title="Doctor" subtitle="The checks the hub runs itself. `vibey doctor` on the host is the full check." onRefresh={reload}>
      <Loaded result={result}>
        {(doctor) =>
          present.doctor(doctor).map((row) => (
            <Card key={row.name} role={row.role}>
              <Label strong>{row.name}</Label>
              <Pill role={row.role}>{row.role === 'success' ? 'PASS' : row.role === 'warning' ? 'WARN' : 'FAIL'}</Pill>
              <Label tone="secondary">{row.detail}</Label>
            </Card>
          ))
        }
      </Loaded>
    </Screen>
  );
}
