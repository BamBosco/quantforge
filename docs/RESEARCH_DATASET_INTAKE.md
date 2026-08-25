# Unseen Research Dataset Intake

This procedure prepares raw exports for research without reading market-bar
contents. It is not replay authorization and it does not permit paper mode or
MT5 changes.

## Controlled structure

Initialize the two role-separated directories once:

```zsh
python3 tools/freeze_research_dataset.py init --root data/research_unseen
```

The command creates `evaluation` and `confirmation` with mode `0700`. Save each
raw export directly in its corresponding directory; do not open it in an editor,
spreadsheet, importer, or charting tool.

## Freeze procedure

Record the source, terminal-local source timezone, retrieval time, and selected
coverage from the MT5 export operation. Do not infer them from bar contents.
Then run `freeze` once for the raw file. It reads raw bytes only to calculate
SHA-256, validates the declared coverage against the viewed-data registry, writes
an immutable manifest, and changes the raw export and manifest to owner-read-only.
It does not parse CSV rows or assess data quality.

Quality status is intentionally `unassessed` at this point. A later, separately
authorized structural quality check may update neither the raw export nor its
manifest; it must produce a separate quality report that references the frozen
raw-file SHA-256.

The manifest includes source/provenance, retrieval metadata, source timezone,
declared UTC coverage, checksum, unassessed quality metadata, and access-control
metadata. It rejects any declared overlap with a previously viewed dataset from
the **same venue** in
[`viewed_data_registry.json`](../config/datasets/viewed_data_registry.json).
It also rejects overlap with a manifest already frozen in the other role.

## Candidate 001 acquisition targets

These are requested source-local calendar ranges, not claims about observed bar
coverage. They are deliberately separated from the previously viewed interval
beginning 2023-08-14 UTC and from each other. Each four-year request provides a
large buffer above the frozen 709-valid-session requirement; availability and
quality remain unassessed until a later authorized structural check.

| Role | Select in MT5 Bars export | Save directly to |
| --- | --- | --- |
| Evaluation | `2019-08-12 00:00` through `2023-08-11 23:59` in the terminal's recorded local export timezone | `data/research_unseen/evaluation/` |
| Confirmation | `2015-08-10 00:00` through `2019-08-09 23:59` in the terminal's recorded local export timezone | `data/research_unseen/confirmation/` |

## Manual MT5 export procedure

1. Before exporting, record the Mac/terminal local IANA timezone in use. Do not
   rely on the chart-server timezone and do not change the local timezone between
   selecting the range and exporting.
2. In the existing Headway Demo terminal, open **View → Symbols**, choose
   `XAUUSD`, then its **Bars** tab. Select **M1**, request the applicable range
   above, and use the built-in **Export** action to create the tab-delimited MT5
   bars CSV. This is the same standard MT5 Bars export whose format includes
   date, time, OHLC, tick volume, and spread.
3. Save the file directly to its role directory above. Do not open, preview,
   import, chart, or otherwise read the exported file.
4. Record only export-operation facts: source `Headway Demo MT5`, instrument
   `XAUUSD`, M1, local source timezone, retrieval time in UTC, and the selected
   requested range. Then run the `freeze` command with those facts and the
   corresponding requested UTC boundaries. The command hashes bytes and locks
   the file; it does not inspect bars.
5. Repeat independently for the confirmation range. Do not reuse, copy, append
   to, or merge either raw export.
