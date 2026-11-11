"""Freeze the whipsaw-day study before any outcome: protocol, event code, inputs and blind counts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import rtl_weekly_engine as engine
import whipsaw_days as wd
from project_paths import PROJECT_ROOT as ROOT
from verify_rtl_failed_breakout_short import CACHE

DOC = ROOT / 'docs/baseline/whipsaw-days'
RUN = ROOT / 'Reports/whipsaw_days_20261111'
PROTOCOL = DOC / 'PROTOCOL.md'
FREEZE = DOC / 'freeze.json'
LEDGERS = {'gg': ROOT / 'Reports/gg_size_cap_20261111/ggcap_20261111_base_control_trades.csv',
           'rtl': ROOT / 'Reports/rtl_gg_exclude16_20261101/ex16_20261101_rtl_base_all_trades.csv'}
NEWS = ROOT / 'data/calendars/us_major_news_times_2010_2026.csv'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def text_digest(path):
    """SHA-256 with CRLF normalized, so checkout line endings cannot break the freeze."""
    return hashlib.sha256(Path(path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def frozen_texts():
    return {'protocol_sha256': text_digest(PROTOCOL), 'event_code_sha256': text_digest(wd.__file__)}


def main():
    if FREEZE.exists():
        raise RuntimeError('Already frozen: freeze.json is kept as it is')
    panel = wd.event_panel(wd.read_m30())
    found = wd.counts(panel)
    assert found == wd.EXPECTED_COUNTS, found
    inputs = [wd.READY_M30, CACHE, engine.MINUTES, engine.ROLLS, *LEDGERS.values(), NEWS]
    record = dict(
        study='Whipsaw sessions before a large move (NQ M30 event study)',
        frozen_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'),
        outcomes_computed_before_freeze=False,
        **frozen_texts(),
        digest_note='protocol and event code: SHA-256 of the text with CRLF normalized to LF; inputs: raw bytes',
        first_session=str(panel.index[0].date()), last_session=str(panel.index[-1].date()),
        counts=found,
        counts_by_era={era: {name: int(panel.loc[wd.in_era(panel, era), name].sum()) for name in wd.EVENTS}
                       for era in wd.ERAS},
        inputs_sha256={str(Path(p).relative_to(ROOT)) if Path(p).is_relative_to(ROOT) else str(p): digest(p)
                       for p in inputs})
    text = json.dumps(record, indent=2)
    RUN.mkdir(parents=True, exist_ok=True)
    FREEZE.write_text(text, encoding='utf-8')
    (RUN / 'freeze.json').write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
