# Capability matrix

The runner — `gptossloop` and `qwenloop` alike, one Typer application under two
names (vibey ADR-0064) — exposes the literal top-level command union of claudeloop, codexloop,
and the two paid runners vibey ADR-0078 later retired. Core lifecycle, control, model, server, doctor,
identity, and usage commands have native local behavior. Vendor account,
cloud, resource, speech, and generated API families are local equivalents and
never call the original vendors. Each command is registered through the same
Typer application and is covered by the CLI command-presence contract test.

