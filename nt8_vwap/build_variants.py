"""Build additive NT8 VWAP variants from the user's existing strategies."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
SOURCES = [
    Path(r'I:\PycharmProjects\RT30_min_nt8_standalone\RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_MaxRedRun.cs'),
    Path(r'I:\PycharmProjects\Accounts_staggering\nt8\RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_Routed_MaxRedRun.cs'),
]

PROPERTIES = '''        // ===== MT5 SESSION VWAP EXPERIMENT =====
        [NinjaScriptProperty]
        [Display(Name = "Use VWAP gate", Order = 0, GroupName = "VWAP")]
        public bool UseVwapGate { get; set; }

        [NinjaScriptProperty]
        [Range(-100.0, 100.0)]
        [Display(Name = "Far-below Z", Order = 1, GroupName = "VWAP",
            Description = "Reject a red M30 signal only when Close < minute-volume VWAP + Z * A20. MT5 research value: -1. A20 is a simple mean of 20 true ranges, not Wilder ATR.")]
        public double VwapFarBelowZ { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "Anchor minute", Order = 2, GroupName = "VWAP",
            Description = "Minutes after midnight on the shifted session clock. 0 matches the futures study; 570 is 09:30 for stocks with New York time and zero shift.")]
        public int VwapAnchorMinute { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Session time zone ID", Order = 3, GroupName = "VWAP",
            Description = "Windows time zone ID. Central Standard Time handles Chicago DST automatically. NT8's configured chart time zone is converted to this zone before the shift.")]
        public string VwapSessionTimeZoneId { get; set; }

        [NinjaScriptProperty]
        [Range(-1440, 1440)]
        [Display(Name = "Session clock shift (minutes)", Order = 4, GroupName = "VWAP",
            Description = "480 with Chicago time matches MT5's Chicago + 8 hour date (rollover 16:00 Chicago, regular CME open 17:00). This is not a fixed UTC offset.")]
        public int VwapSessionShiftMinutes { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Show VWAP indicator", Order = 5, GroupName = "VWAP")]
        public bool ShowVwapIndicator { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Log VWAP decisions", Order = 6, GroupName = "VWAP",
            Description = "Print candidate close, VWAP, A20, threshold and decision to NinjaScript Output. Unknown values allow entries, matching MT5.")]
        public bool LogVwapDecisions { get; set; }

'''

METHOD = '''        // Called only for a red entry candidate, after open-position exits.
        // A previous-session signal at the next session open is unknown, as in MT5.
        private bool IsVwapEntryRejected(DateTime windowTime)
        {
            if (!UseVwapGate && !LogVwapDecisions)
                return false;

            bool sameSession = sessionVwap != null
                && sessionVwap.SessionDate(Time[0].AddMinutes(-30))
                    == sessionVwap.SessionDate(windowTime);
            bool known = sameSession && sessionVwap.IsKnown;
            double vwap = known ? sessionVwap.SessionVWAP[0] : double.NaN;
            double a20 = known ? sessionVwap.A20[0] : double.NaN;
            double gate = known ? sessionVwap.GateLine[0] : double.NaN;
            bool rejected = UseVwapGate && known && Close[0] < gate;

            if (LogVwapDecisions || rejected)
                Print(string.Format(System.Globalization.CultureInfo.InvariantCulture,
                    "[{0:yyyy-MM-dd HH:mm:ss}] [{1}] VWAP gate: close={2:R}, vwap={3:R}, "
                    + "A20={4:R}, line={5:R}, known={6}, enabled={7}, decision={8}",
                    Time[0], EntrySignalName, Close[0], vwap, a20, gate, known, UseVwapGate,
                    rejected ? "SKIP" : (known ? "ALLOW" : "ALLOW (unknown)")));
            return rejected;
        }

'''

def replace_once(text, before, after):
    assert text.count(before) == 1, (before[:150], text.count(before))
    return text.replace(before, after, 1)


def build(source):
    original_bytes = source.read_bytes()
    original = original_bytes.decode('utf-8-sig')
    text = original.replace('\r\n', '\n')
    routed = '_Routed_' in source.name
    old_class = ('RRLongTimeWinStopLimitTPlimitGAPWindowRROffsetsSafeExits'
                 + ('Routed' if routed else '') + 'MaxRedRun')
    new_class = old_class + 'VWAP'
    assert text.count('public class ' + old_class + ' : Strategy') == 1
    text = text.replace(old_class, new_class)
    text = replace_once(text, 'private const string ScriptVersion = "2026.10.22";',
                        'private const string ScriptVersion = "2026.10.29-vwap.1";')
    text = replace_once(text, 'using NinjaTrader.NinjaScript;\n',
                        'using NinjaTrader.NinjaScript;\nusing NinjaTrader.NinjaScript.Indicators;\n')
    text = replace_once(text, '        private Order longOrder;',
                        '        private RTLSessionVWAP sessionVwap;\n\n        private Order longOrder;')
    text = replace_once(text, '        // ===== RED-RUN ENTRY FILTER =====',
                        PROPERTIES + '        // ===== RED-RUN ENTRY FILTER =====')
    text = replace_once(text, '                Description = "Version " + ScriptVersion;',
                        '                Description = "MT5 minute-volume VWAP experiment. Version " + ScriptVersion;')
    text = replace_once(text, '                MaxRedRun = 0;', '''                UseVwapGate = true;
                VwapFarBelowZ = -1.0;
                VwapAnchorMinute = 0;
                VwapSessionTimeZoneId = "Central Standard Time";
                VwapSessionShiftMinutes = 480;
                ShowVwapIndicator = true;
                LogVwapDecisions = false;
                MaxRedRun = 0;''')
    text = replace_once(text, '            else if (State == State.DataLoaded)\n', '''            else if (State == State.Configure)
            {
                // Must mirror RTLSessionVWAP's hardcoded secondary series.
                AddDataSeries(BarsPeriodType.Minute, 1);
            }
            else if (State == State.DataLoaded)
''')
    text = replace_once(text, '                sessionIterator = new SessionIterator(Bars);', '''                sessionIterator = new SessionIterator(Bars);
                if (UseVwapGate || ShowVwapIndicator || LogVwapDecisions)
                {
                    if (BarsPeriod.BarsPeriodType != BarsPeriodType.Minute || BarsPeriod.Value != 30
                        || Calculate != Calculate.OnBarClose)
                        throw new InvalidOperationException("The MT5 VWAP experiment requires 30-minute bars and Calculate.OnBarClose.");
                    sessionVwap = RTLSessionVWAP(Closes[0], VwapFarBelowZ, VwapAnchorMinute,
                        VwapSessionTimeZoneId, VwapSessionShiftMinutes);
                    if (ShowVwapIndicator)
                        AddChartIndicator(sessionVwap);
                }
''')
    text = replace_once(text, '        private bool ExceedsMaxRedRun()', METHOD + '        private bool ExceedsMaxRedRun()')
    text = replace_once(text, '''        protected override void OnBarUpdate()
        {
''', '''        protected override void OnBarUpdate()
        {
            // Minute bars feed the indicator only. All orders retain primary-bar timing.
            if (BarsInProgress != 0)
                return;
            // Warm history and keep the plot current even outside windows/in a position.
            if (sessionVwap != null)
                sessionVwap.Update();

''')
    if routed:
        text = replace_once(text, '            double candidateEntryPrice = High[0];', '''            // False follows the existing rejected-red cancellation path; it does
            // not release the router reservation before the order callback.
            if (IsVwapEntryRejected(windowTime))
                return false;

            double candidateEntryPrice = High[0];''')
        text = replace_once(text, '            sb.Append("|frozen_offset=")', '''            // Gate-off keeps the legacy manifest. Gate-on seats must share the
            // calculation version, threshold, anchor and session clock.
            if (UseVwapGate)
            {
                sb.Append("|vwap=mt5-m1-hlc3-a20-v1");
                sb.Append("|vwap_z=").Append(VwapFarBelowZ.ToString("R", CultureInfo.InvariantCulture));
                sb.Append("|vwap_anchor=").Append(VwapAnchorMinute.ToString(CultureInfo.InvariantCulture));
                sb.Append("|vwap_zone=").Append(VwapSessionTimeZoneId);
                sb.Append("|vwap_shift=").Append(VwapSessionShiftMinutes.ToString(CultureInfo.InvariantCulture));
            }
            sb.Append("|frozen_offset=")''')
        text = text.replace('// R:R/risk, or gap).', '// VWAP, R:R/risk, or gap).')
    else:
        text = replace_once(text, '\t\t\t\tentryPrice = High[0];', '''                if (IsVwapEntryRejected(windowTime))
                {
                    if (IsActiveOrder(longOrder) &&
                        longOrder.OrderState != OrderState.CancelPending &&
                        longOrder.OrderState != OrderState.CancelSubmitted)
                        CancelOrder(longOrder);
                    return;
                }

\t\t\t\tentryPrice = High[0];''')
    text = '// Custom VWAP variant; original strategy remains a separate type.\n// Requires Indicators/RTLSessionVWAP.cs (install once for both variants).\n' + text
    destination = ROOT / (source.stem + '_VWAP.cs')
    destination.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
    return dict(source=str(source), source_sha256=hashlib.sha256(original_bytes).hexdigest(),
                output=destination.name, strategy=new_class)


if __name__ == '__main__':
    manifest = [build(source) for source in SOURCES]
    (ROOT / 'sources.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    for entry in manifest:
        print(entry['output'])
