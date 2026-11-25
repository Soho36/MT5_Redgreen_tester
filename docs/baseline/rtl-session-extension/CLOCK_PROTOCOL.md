# How unusual is the rally at the time of the next order?

Exploratory follow-up, November 24, 2026. Use Q24's capped RTL and dates (2016–19 and January 2020 through July 13, 2026), one MNQ and $1.05 round turn. Preserve the fixed-percent result.

At the opening quote of the submission minute, calculate the percentage move from this session's first open. Rank it against the returns at the exact same exchange-clock minute in the previous 60 trading sessions, including sessions without RTL trades. Use actual opening prices, omit missing reference minutes and require at least 40. Rank ties halfway. The primary unusual rally is a strictly positive return with rank at least 90%. Recheck at 80% and 95%. An unscored order is eligible as usual.

Clock time alone cannot measure how volatile today has been. As a sensitivity use the 60 most similar of the previous 120 sessions available at that minute (require at least 60), by absolute distance in realized volatility from the session open. Measure volatility as the square root of summed squared log changes between successive minute opens through submission. No later quote from the current minute is used. Keep the 90% cutoff.

Report next-trade outcomes by rally and prior realized session P&L, and replay skipping the rally alone, the rally while green, and green P&L alone. Positive net dollars are primary, cumulative realized +1R is secondary. Recompute each policy's own state after each taken trade. Compare net dollars and maximum closed-trade drawdown separately.

Within primary unusual rallies, compare green versus flat/negative session mean net R. Also compare after at least one closed trade, standardizing within shared cells by rank (90–<95 or 95–100), clock time (three-hour blocks) and number of prior trades (1, 2, 3+). Weight cell differences by the number of trades in the shared cells. Use paired calendar-week resampling for uncertainty and report common support. Report both eras separately, yearly effects, weaker and stronger thresholds, and the volatility sensitivity. A common direction and material benefit in both eras matter more than the best threshold. Historical results support exploration only.
