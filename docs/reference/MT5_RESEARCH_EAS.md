# MT5 research EA folders

Updated 2026-10-11. Installed research EAs are grouped by their purpose. The folder is a research category; the selected input parameters still determine the run.

| MT5 Experts folder | EAs / purpose |
|---|---|
| CodexBaselineResearch | RTL_runband, GG_runband, RTL_signal, RTL_granularity, RTL_path, RTL_paths, RTL_width, RTL_breakeven, RTL_short_mirror: baseline entries, controls, resolution, paths, width, break-even and the short mirror |
| CodexLevelResearch | RTL_level_gate, RR_r_MFE_buy-stop-entry_breakout, RTL_support_reclaim: horizontal levels |
| CodexTrendlineResearch | RTL_resistance_gate, RTL_trendline_breakdown, RTL_trendline_limit, RTL_trendline_limit_manual: trendline setups |
| CodexTrendResearch | RTL_trend_rr: trend-regime-conditioned target research |
| CodexSupportResearch | RTL_support_fixed1r: support-context research |
| CodexAveragingResearch | RTL_average |
| CodexLimitOnlyResearch | RTL_limit_only |
| CodexExitResearch | RTL_exit_comparison |
| CodexBarResearch | RTL_runband_snapshot |
| CodexLocationValidation | RTL_base and RTL_runband_location: location-filter comparisons |
| ClaudeEarlyClose / ClaudeFlattenFix / ClaudeTrailingStop / ClaudeSessionDump | Existing calendar, flatten, trailing and session-export tools |

The RTL_width experiment EA is now under:

~~~text
MQL5\Experts\CodexBaselineResearch\RTL_width.ex5
~~~

For that EA, RTL uses SignalMode=0, MaxRedRun=3; the market-buy control uses SignalMode=3, MaxRedRun=0. Its retained last-used inputs are the filtered control (RunTag=width_20261011_control_min50). Moving it does not change those inputs.

## Installation and saved runs

[Folder routing](../../python/mt5_expert_layout.py) supplies the correct EA installation directory to the [shared runner](../../python/run_mt5_job.py). Unknown research EAs default to the neutral CodexResearch folder until classified.

Recorded study INIs retain their original Expert paths. The shared runner creates a launch copy in the run folder's .mt5_runtime/ directory when a path needs translating. Only the Expert value changes; inputs, dates, modelling and report labels are preserved. Do not bulk-edit historical reports or their manifests to rename a folder.

## Relocation record

Nine baseline EAs and the horizontal support-reclaim EA were moved out of the trendline folder on 2026-10-11, together with their required local includes. Source and compiled files retain their exact hashes. Four actual trendline EAs remain. The other installed research folders were checked and already describe their EAs' purpose; generic legacy/archive and bundled example folders were left in place.

[Relocation plan and hashes](../../Reports/mt5_ea_relocation_20261011/plan.json), [completion record](../../Reports/mt5_ea_relocation_20261011/completed.json), and backups are in Reports/mt5_ea_relocation_20261011/. Six retained terminal/tester paths were updated.

This maintenance changes the shared Python runner after the width experiment's freeze. Its [exact prior source](../../Reports/mt5_ea_relocation_20261011/previous_run_mt5_job.py) and [prior Git revision](../../Reports/mt5_ea_relocation_20261011/preparation.json) are preserved. Checks that require the study's exact frozen tooling must use that recorded version; the study's EA source, inputs, ledgers and results were not rewritten.

Refresh MT5's Navigator to display the new folders. If an already-open tester still displays the old location, select the EA from its new folder.
