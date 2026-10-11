* **`vibey worker --auto-accept-design` and `--accept-spec-json`:** an unattended local run no
  longer stops at `vibey design accept` once the operator has already decided. The flag accepts
  the project's DESIGN spec when DESIGN has settled (no DESIGN job of the cycle unsettled, a
  spec present), through the same acceptance service and guards as the manual command, so an
  open blocking question still refuses it. With `--accept-spec-json PATH` it imports that
  reviewed spec first, as `design accept --spec-json` does. It is the operator's consent for one
  worker and one project (refused with `--all-projects`), says what it will do at startup, never
  opts into VISUAL_DESIGN, accepts once, and the ledger's visual-design event records
  `accepted_by: auto-accept-design`. `--auto-answer` is unchanged and still never answers an
  acceptance. Before, an accepted-in-advance spec still waited for a person to run the command.
