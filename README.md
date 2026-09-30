# RTL strategy research

MT5 expert advisors and Python research tools for bar-only entry experiments.
Run the commands below from this project root. The existing `venv/` stays here.

## Where things live

| Path | Contents |
|---|---|
| `mt5/experts/` | Current MT5 sources, including the base, runband, and feature EAs |
| `mt5/experts/shorts/`, `mt5/experts/window_rr/` | Specialized variants |
| `mt5/archive/` | Older strategies, preserving the user's archived files |
| `python/` | Analysis and verification command-line scripts |
| `docs/` | Research questions, protocols, findings, and diagrams |
| `data/legacy/` | Historical CSVs with potentially different settings |
| `Reports/` | Generated runs, INIs, compiler logs, CSVs, HTML reports; gitignored |

The `.cs` files contain **MQL5**, not C#. Their names are retained to preserve
history. Compile a copied `.mq5` file with MetaEditor, or use the optional
`SnapshotBars` input in the runband EA for research exports. Installed terminal
copies are separate from these project sources.

Start with [research results](docs/RESEARCH_RESULTS.md) and the
[question checklist](docs/RESEARCH_QUESTIONS.md). The
[preceding-bar protocol](docs/PRECEDING_CANDLES_PROTOCOL.md) fixes the definitions
for the first two questions before inspecting their outcomes. Their
[first study is complete](docs/PRECEDING_CANDLES_RESULTS.md); neither new filter
was adopted.

The [exit and data review](docs/EXIT_AND_DATA_REVIEW.md) reproduces the +1R
first-touch estimate and records the synthetic session clock, outstanding
data-provenance questions, and proposed next research direction.
The subsequent [full MT5 exit study](docs/EXIT_THRESHOLD_RESULTS.md) compares
five bar-close thresholds and fixed TP 1R. It keeps 1R as baseline pending a
session-clock check of cross-date positions; 2R remains a research candidate.

## Existing commands

```powershell
.\venv\Scripts\python.exe python\analyze_features.py --list
.\venv\Scripts\python.exe python\analyze_features.py --feature location --commission 1
.\venv\Scripts\python.exe python\analyze_runlength.py data\legacy\trade_stats_rr_1.0.csv --commission 1
.\venv\Scripts\python.exe python\verify_location_validation.py Reports\location_validation_20260929
.\venv\Scripts\python.exe python\evaluate_maxredrun_train.py Reports\maxredrun_train_20260929
.\venv\Scripts\python.exe python\analyze_preceding_candles.py Reports\preceding_candles_20260930
.\venv\Scripts\python.exe python\estimate_first_touch.py
.\venv\Scripts\python.exe -m unittest discover -s python -p "test_*.py" -v
```

The legacy CSV is not a matching baseline for the current runs. Scripts in
`python/` import one another from that directory when launched as above.
Pass explicit CSV paths for reproducible research; automatic discovery is a
convenience for older commands. Python research needs NumPy; `analyze_drop.py
--plot` additionally uses matplotlib. Verification uses the standard library.

The current research candidate is `MaxRedRun=3`, `MinLocation=0`. Strategy
defaults are not changed by the research setup. No test shown here establishes
live profitability or untouched out-of-sample confirmation.
