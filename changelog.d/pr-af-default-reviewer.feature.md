* **pr-af as the declared default reviewer:** Agent-Field `pr-af` reviews every pull
  request's exact head from a GitHub-hosted runner by default, with the operator's own
  runner as an opt-in venue. Its own merge gate is authoritative while it has a verdict; a
  missing secret, an unreachable control plane or a spent budget leaves no verdict, so the
  sovereign/paid lane decides instead. ADR-0090.
