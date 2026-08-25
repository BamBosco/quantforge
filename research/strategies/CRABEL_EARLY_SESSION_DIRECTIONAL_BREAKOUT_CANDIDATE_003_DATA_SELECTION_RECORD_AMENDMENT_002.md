# Candidate 003 — Data-Selection Record Amendment 002

## Identity and status

**Candidate ID:** `crabel_early_session_directional_breakout_candidate_003`

**Amends:** Amendment 001 to the Candidate 003 frozen pre-inspection selection
record.

**Amendment version:** `0.1.2-frozen-pre-inspection`

**Status:** Frozen provenance clarification. This changes no trading rule,
research threshold, role assignment, or authorization.

## Confirmed export-clock provenance

The operator confirmed that the MT5/Wine export clock uses the Mac's
`Africa/Lagos` / WAT timezone (`UTC+01:00`) with no MT5 timezone override.
The evaluation export-operation boundaries declared in Amendment 001 therefore
normalize as follows:

| Terminal-export clock | UTC-normalized boundary |
| --- | --- |
| `2019-08-01 01:05` WAT | `2019-08-01T00:05:00+00:00` |
| `2023-08-01 23:54` WAT | `2023-08-01T22:54:00+00:00` |

The selected raw-file coverage for manifest purposes is exactly
`2019-08-01T00:05:00+00:00` through `2023-08-01T22:54:00+00:00`.

No raw market-data row was opened, parsed, previewed, imported, or evaluated
to make this clarification. The expected CSV remains evaluation-only;
confirmation remains untouched. The >=709 complete-session requirement and all
Candidate 003 rules remain unchanged.
