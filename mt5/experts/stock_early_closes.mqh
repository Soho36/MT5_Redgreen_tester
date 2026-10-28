// US stock early closes: Nasdaq/NYSE regular session ends at 13:00 New York time.
// 2018-2025: detected in the Databento XNAS data of the VWAP stock test (afternoon volume near
// zero) and present in the exchange calendar. 2026: Nov 27 and Dec 24 from the published
// calendar (check before live use). Clock: New York time, as in the exported stock CSVs.
// SEC_FLAT_MIN = flatten minute after midnight (12:30, the last M30 bar before the close).
#define SEC_COUNT 20
const int SEC_DATE[SEC_COUNT] = {20180703,20181123,20181224,20190703,20191129,20191224,20201127,20201224,
                                 20211126,20221125,20230703,20231124,20240703,20241129,20241224,20250703,
                                 20251128,20251224,20261127,20261224};
const int SEC_FLAT_MIN[SEC_COUNT] = {750,750,750,750,750,750,750,750,750,750,750,750,750,750,750,750,
                                     750,750,750,750};
