"""Prepare the short mirror of GG_outside: sell stop below a GREEN outside bar.

All signal and session rules match GG_outside. The directional order, stop,
bar-close target, and optional trailing stop are mirrored. This script generates
an isolated research EA and INIs; the long GG EA remains unchanged.
"""
import json
import shutil

from prepare_gg_outside import (ROOT, SETTINGS, BASE_INI, build_source, once)

EXPERT = "GG_outside_short"
STUDY = ROOT / "Reports" / "gg_outside_short_20261020"


def build_short_source():
    src = build_source()
    src = once(src, "input bool   UseOutsideFilter = false;",
               "input bool   UseOutsideFilter = true;")
    src = src.replace("CancelOldBuyStops()", "CancelOldSellStops()")
    src = src.replace("BuyStop", "SellStop")
    src = once(src, "if(type != ORDER_TYPE_BUY_STOP) continue;",
               "if(type != ORDER_TYPE_SELL_STOP) continue;")
    src = once(src, "if(typ != POSITION_TYPE_BUY) return;",
               "if(typ != POSITION_TYPE_SELL) return;")
    src = once(src, "double target = g_initialEntry + g_initialRisk * RiskReward;",
               "double target = g_initialEntry - g_initialRisk * RiskReward;")
    src = once(src, "if(barClose >= target)", "if(barClose <= target)")
    src = once(src, """      req.volume    = vol; // closes full net position
      req.type      = ORDER_TYPE_SELL;
      req.price     = SymbolInfoDouble(_Symbol, SYMBOL_BID);""",
               """      req.volume    = vol; // closes full net position
      req.type      = ORDER_TYPE_BUY;
      req.price     = SymbolInfoDouble(_Symbol, SYMBOL_ASK);""")
    src = once(src, "if(sl > 0.0 && entry > sl)",
               "if(sl > entry && entry > 0.0)")
    src = once(src, "g_initialRisk  = entry - sl;",
               "g_initialRisk  = sl - entry;")
    src = src.replace("g_trailHigh", "g_trailLow")
    src = once(src, """   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   g_trailLow = MathMax(g_trailLow, bid);
   if(g_trailLow < g_initialEntry + TrailStartR * g_initialRisk) return;

   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick <= 0.0) tick = _Point;
   double newSl = MathFloor((g_trailLow - TrailDistanceR * g_initialRisk) / tick) * tick;
   newSl = NormalizeDouble(newSl, _Digits);

   double curSl  = PositionGetDouble(POSITION_SL);
   double minGap = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(newSl < curSl + tick || newSl > bid - minGap - tick) return;""",
               """   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   g_trailLow = MathMin(g_trailLow, ask);
   if(g_trailLow > g_initialEntry - TrailStartR * g_initialRisk) return;

   double tick = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tick <= 0.0) tick = _Point;
   double newSl = MathCeil((g_trailLow + TrailDistanceR * g_initialRisk) / tick) * tick;
   newSl = NormalizeDouble(newSl, _Digits);

   double curSl  = PositionGetDouble(POSITION_SL);
   double minGap = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(newSl > curSl - tick || newSl < ask + minGap + tick) return;""")
    src = once(src, "double   g_trailLow       = 0.0; // highest bid since entry (trailing stop)",
               "double   g_trailLow       = 0.0; // lowest ask since short entry (trailing stop)")
    src = once(src, "// Tick-level trailing stop for the open long position",
               "// Tick-level trailing stop for the open short position")
    src = once(src, "// BUY-STOP ORDER AT PREVIOUS GREEN CANDLE HIGH",
               "// SELL-STOP ORDER AT PREVIOUS GREEN OUTSIDE CANDLE LOW")
    src = once(src, "   double entry = h1;", "   double entry = l1;")
    src = once(src, "   double stop  = l1;", "   double stop  = h1;")
    src = once(src, "   double risk  = entry - stop;", "   double risk  = stop - entry;")
    src = once(src, "req.type         = ORDER_TYPE_BUY_STOP;",
               "req.type         = ORDER_TYPE_SELL_STOP;")
    src = once(src, '-> place Buy Stop");', '-> place Sell Stop");')
    src = once(src, 'Print("Place Buy Stop failed err="', 'Print("Place Sell Stop failed err="')
    src = once(src, 'Print("Buy Stop placed @"', 'Print("Sell Stop placed @"')
    return src


def main():
    STUDY.mkdir(parents=True, exist_ok=True)
    (STUDY / f"{EXPERT}.mq5").write_text(build_short_source(), encoding="utf-8")
    shutil.copyfile(ROOT / "mt5" / "experts" / "early_closes.mqh",
                    STUDY / "early_closes.mqh")
    template = BASE_INI.read_text(encoding="utf-16")
    jobs = []
    settings = [(None, None, None)] + SETTINGS
    for n, ratio, overhang in settings:
        if n is None:
            tag = "ggshort_20261020_control"
            extra = "UseOutsideFilter=false\n"
        else:
            tag = f"ggshort_20261020_n{n}_r{ratio:g}_o{overhang:g}".replace(".", "p")
            extra = (f"UseOutsideFilter=true\nOutsideLookback={n}\n"
                     f"MinOutsideRangeRatio={ratio}\n"
                     f"MinOutsideOverhangFraction={overhang}\n")
        ini = once(template, "Expert=CodexBaselineResearch\\GG_runband.ex5",
                   f"Expert=CodexBaselineResearch\\{EXPERT}.ex5")
        ini = once(ini, "Report=gggreen_20261020_cap0.htm", f"Report={tag}.htm")
        ini = once(ini, "RunTag=gggreen_20261020_cap0", f"RunTag={tag}")
        ini = once(ini, "SnapshotBars=0\n", "SnapshotBars=0\n" + extra)
        (STUDY / f"{tag}.ini").write_text(ini, encoding="utf-16")
        jobs.append({"tag": tag, "n": n, "range_ratio": ratio,
                     "overhang_fraction": overhang,
                     "outputs": [f"runband_{tag}_1.00.csv",
                                 f"runband_{tag}_1.00_stats.csv"]})
    (STUDY / "manifest.json").write_text(json.dumps({
        "expert": EXPERT, "long_study": "gg_outside_20261020",
        "description": "Green outside signal, sell stop at low, SL at high, 1R bar-close exit",
        "jobs": jobs}, indent=2), encoding="utf-8")
    print(f"Prepared {len(jobs)} short jobs in {STUDY}")


if __name__ == "__main__":
    main()

