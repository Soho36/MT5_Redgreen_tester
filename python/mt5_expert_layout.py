"""MT5 research EA folders and runtime paths for immutable saved tester jobs."""
import re
from pathlib import Path, PureWindowsPath


BASELINE_EXPERTS = frozenset({
    "GG_runband", "RTL_breakeven", "RTL_granularity", "RTL_path",
    "RTL_paths", "RTL_runband", "RTL_short_mirror", "RTL_signal", "RTL_width",
})
TRENDLINE_EXPERTS = frozenset({
    "RTL_resistance_gate", "RTL_trendline_breakdown",
    "RTL_trendline_limit", "RTL_trendline_limit_manual",
})
EXPERT_FOLDERS = {
    **dict.fromkeys(BASELINE_EXPERTS, "CodexBaselineResearch"),
    **dict.fromkeys(TRENDLINE_EXPERTS, "CodexTrendlineResearch"),
    "RTL_support_reclaim": "CodexLevelResearch",
    "RTL_level_gate": "CodexLevelResearch",
    "RR_r_MFE_buy-stop-entry_breakout": "CodexLevelResearch",
    "RTL_trend_rr": "CodexTrendResearch",
    "RTL_average": "CodexAveragingResearch",
    "RTL_limit_only": "CodexLimitOnlyResearch",
    "RTL_support_fixed1r": "CodexSupportResearch",
    "RTL_runband_snapshot": "CodexBarResearch",
    "RTL_exit_comparison": "CodexExitResearch",
    "RTL_runband_location": "CodexLocationValidation",
}


def expert_folder(expert):
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", expert) or ".." in expert:
        raise ValueError(f"Invalid EA name: {expert!r}")
    # Unknown research EAs get a neutral folder, never an assumed strategy label.
    return EXPERT_FOLDERS.get(expert, "CodexResearch")


def tester_expert_path(expert):
    return f"{expert_folder(expert)}\\{expert}.ex5"


def runtime_tester_config(run, tag, expert):
    """Change only Expert in a launch copy; preserve the recorded original INI."""
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", tag) or ".." in tag:
        raise ValueError(f"Invalid run tag: {tag!r}")
    original = Path(run) / f"{tag}.ini"
    raw = original.read_bytes()
    encoding = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else (
        "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    )
    text = raw.decode(encoding)
    matches = list(re.finditer(r"^Expert=([^\r\n]+)", text, re.MULTILINE))
    if len(matches) != 1:
        raise ValueError(f"Expected one Expert setting in {original}")
    old = matches[0].group(1)
    if PureWindowsPath(old).name.casefold() != f"{expert}.ex5".casefold():
        raise ValueError(f"INI selects {old!r}, expected {expert}.ex5")
    new = tester_expert_path(expert)
    if old == new:
        return original
    match = matches[0]
    text = text[:match.start(1)] + new + text[match.end(1):]
    destination = Path(run) / ".mt5_runtime" / original.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(text.encode(encoding))
    return destination
