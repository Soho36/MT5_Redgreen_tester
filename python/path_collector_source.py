"""Add passive complete-path diagnostics to an unchanged signal-colour EA.

The wrapper preserves every original OnTick return and never writes original
strategy globals. Complete original order/deal and raw-ledger replication must
be verified after each instrumented run.
"""

from prepare_signal_colour import build_source as signal_colour_source


def build_source():
    source = signal_colour_source()
    edits = (
        ('// ======== HELPER FUNCTIONS ========\n',
         '#include "path_research.mqh"\n\n// ======== HELPER FUNCTIONS ========\n'),
        ('   DisplaySettings();\n   return(INIT_SUCCEEDED);\n',
         '   DisplaySettings();\n   PathResearchInit();\n   return(INIT_SUCCEEDED);\n'),
        ('double OnTester()\n{\n',
         'double OnTester()\n{\n   PathResearchFinishTester();\n'),
        ('void OnTick()\n', 'void StrategyOnTick()\n'),
        ('   double target = g_initialEntry + g_initialRisk * RiskReward;\n',
         '   double target = g_initialEntry + g_initialRisk * RiskReward;\n'
         '   PathResearchTargetCheck(barClose, target);\n'),
        ('\t   else\n\t      Print("Buy Stop placed @", entry);\n',
         '\t   else\n\t   {\n'
         '\t      PathResearchEntryOrder(req, res);\n'
         '\t      Print("Buy Stop placed @", entry);\n'
         '\t   }\n'),
    )
    for old, new in edits:
        if source.count(old) != 1:
            raise ValueError(f'Path observer edit anchor is not unique: {old!r}')
        source = source.replace(old, new)
    source += ('\n\n// Passive wrapper around the original strategy handler.\n'
               'void OnTick()\n{\n'
               '   PathResearchBeforeTick();\n'
               '   StrategyOnTick();\n'
               '   PathResearchAfterTick();\n'
               '}\n')
    return source
