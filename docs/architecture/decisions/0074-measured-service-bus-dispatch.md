# ADR-0074 — Measured dispatch for every service-bus surface

## Status

Accepted by the merge that carries this record.

## Decision

Every surface controlled by a service bus, queue, or RabbitMQ transport exposes
singleton, multiplexer, and bounded hybrid dispatch where semantically available.
The default is `auto`: a bounded experiment runs on the machine and workload that
will use it, records the rates and workload, and selects the fastest policy.
Missing, stale, invalid, or failed measurements fall back to singleton; an
operator may explicitly select a mode.

Selection is per surface and workload. A winner from model-turn dispatch cannot
be applied to orchestration messages, and a result from one machine is not
evidence for another. Measurements are durable and inspectable.

## Rationale

The local experiments showed that model-turn dispatch and the core orchestration
bus can have different winners. Treating RabbitMQ as universally best would make
the default less correct where the machine, payload, and concurrency differ.

## Consequences

- New queue-backed surfaces implement all three policies or document why one is
  semantically impossible and measure the remaining policies.
- Results are invalidated when the workload or implementation version changes.
- No default claims a winner without a recorded measurement.
