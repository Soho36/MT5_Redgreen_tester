# RTL drawdown research: synthesis

2026-10-25. Saved at the user's request after reviewing the completed studies.
This is an interpretation of existing evidence, not another experiment or a
change to the trading baseline.

## What the studies establish

| Study | Finding |
|---|---|
| [Downtrend crystal ball](../rtl-downtrend-oracle/RESULTS.md) | Exact hindsight timing raises net profit 36-202%. For 2% declines, delaying both stop and resume by two sessions eliminates the advantage in both eras. |
| [Early crystal ball](../rtl-downtrend-oracle/EARLY_RESULTS.md) | Both boundaries two sessions early still add 20-59%. Anticipation remains possible in principle, but these signals identify real future declines without false alarms. |
| [Warning rules](../rtl-warning-rules/RESULTS.md) | The early rise-warning rule loses 51% of recent profit through time off during continuing rallies. Bounce-based restarting repairs much of the live zigzag's damage but establishes no robust advantage over controls. |
| [Weekly gate](../rtl-weekly-gate/RESULTS.md) | All tested versions reduce profit 52-85%; skipped trades are generally better than retained ones. |
| [MA agreement](../rtl-ma-agreement/RESULTS.md) | Mixed and downward states contain substantial profits. Their omission does not consistently improve results across eras. |
| [Price structure](../rtl-price-structure/RESULTS.md) and [episodes](../rtl-price-structure/EPISODE_RESULTS.md) | Broad chop/wick flags also contain profitable upward moves. Future path splits are descriptive and occur in unflagged trades too; they do not supply a causal exit or restart rule. |

The obstacle is both identification and timing: avoid enough losses, limit false
alarms in profitable markets, and restart before too much rebound profit passes.
The tested implementations have not achieved this combination consistently.
The crystal balls benchmark particular daily-close zigzag windows; they are not
a mathematical ceiling on every possible filter. Delayed variants move both
boundaries, so they do not isolate stop lag from restart lag.

## Risk reduction is a separate objective

Warning Rule B at 2% reduces recent net profit from $38,399.95 to approximately
$32,815, and daily-close drawdown from $5,781.15 to approximately $4,051: about
15% less profit for 30% less drawdown. Profit/DD improves in both eras. Recent
same-holding static exposure earns about $32,751 with $4,931 DD, but the earlier
comparison and shifted-placement controls do not establish a stable advantage.
Retain this as a risk-management lead, not an adoption case. Lower net profit
alone is not grounds to reject a risk-reduction proposal.

Fixed-$200-risk sizing capped at five contracts was already studied: it improved
net/DD recently but not in 2015-19. Do not present it as an untested cure.
See [status](../../STATUS.md) and [journal](../../JOURNAL.md).

## Practical conclusion and remaining work

Accepting manageable drawdowns currently has stronger support than adopting our
tested timing filters. This does not justify unlimited losses, guarantee recovery,
or establish an acceptable account size. The decision is whether RTL offers
enough credible return for the risk at a feasible contract size.

Before live deployment, assess drawdown duration and depth, clustered losses,
additional slippage, a weaker edge and actual account loss limits. Historical
daily-close DD omits intraday equity extremes and is not a future risk ceiling.
Position size should follow affordable risk rather than available margin; see
[CME risk guidance](https://www.cmegroup.com/education/courses/things-to-know-before-trading-cme-futures/position-and-risk-management).
Forward evidence and predefined review/stop criteria remain necessary: this
history has been repeatedly examined.

A hedge remains a separate, deferred research question. A losing standalone
short may improve joint results, but its synchronized after-cost portfolio
payoff must beat simply reducing RTL exposure. No hedge or filter is adopted.
