"""Verify the VWAP additions preserve GG's existing order-handling methods."""
from pathlib import Path
import hashlib
import json
import re

root = Path(__file__).resolve().parents[1]
changed = {'OnStateChange', 'OnBarUpdate', 'EvaluateEntryCandle', 'BuildRouterConfigKey'}


def methods(text):
    # Blank comments and literals without changing offsets before balancing bodies.
    code = re.sub(r'//[^\n]*|/\*.*?\*/|@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                  lambda m: ' ' * len(m.group()), text, flags=re.S)
    found = {}
    for match in re.finditer(r'^\s*(?:private|protected|public) (?:override )?[\w<>]+ (\w+)\([^;{]*\)\s*\{', code, re.M):
        start = code.index('{', match.start(), match.end())
        depth, end = 1, start + 1
        while depth:
            depth += (code[end] == '{') - (code[end] == '}')
            end += 1
        found[match.group(1)] = text[match.start():end].strip()
    return found


count = 0
for entry in json.loads((root / 'sources_gg.json').read_text()):
    original_bytes = Path(entry['source']).read_bytes()
    assert hashlib.sha256(original_bytes).hexdigest() == entry['source_sha256']
    original = original_bytes.decode('utf-8-sig').replace('\r\n', '\n')
    output = (root / entry['output']).read_text(encoding='utf-8-sig')
    old, new = methods(original), methods(output)
    assert set(old) <= set(new)
    for name in old.keys() - changed:
        assert old[name] == new[name], f"Changed GG method {name} in {entry['output']}"
        count += 1
    bar = new['OnBarUpdate']
    assert bar.index('if (BarsInProgress != 0)') < bar.index('sessionVwap.Update()') < bar.index('if (IsStopFallbackActive())')
    assert bar.index('Position.MarketPosition == MarketPosition.Long') < bar.index('DateTime windowTime')
    if '_Routed_' in entry['output']:
        candidate = new['EvaluateEntryCandle']
        assert candidate.index('Close[0] <= Open[0]') < candidate.index('IsVwapEntryRejected(windowTime)') < candidate.index('MayEnter(candidateRisk)')
        assert 'if (Close[0] > Open[0] && !renewedEntry && IsActiveOrder(longOrder)' in bar
    else:
        assert bar.index('if (Close[0] > Open[0])') < bar.index('IsVwapEntryRejected(windowTime)') < bar.index('entryPrice = High[0]')
        gate = bar[bar.index('if (IsVwapEntryRejected(windowTime))'):bar.index('entryPrice = High[0]')]
        assert 'CancelOrder(longOrder);' in gate and 'return;' in gate
    assert 'public class ' + entry['strategy'] + ' : Strategy' in output
    print('PASS: original hash, GG signal/cancellation placement, and preserved methods:', entry['output'])
print(f'PASS: {count} existing GG methods preserved byte-for-byte after newline normalization.')
