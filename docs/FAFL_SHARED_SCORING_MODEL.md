# FAFL shared scoring model — F315, no extra growth

One engine supplies H2H, All-Play, all four quarterly Bonus Games, the Reg Season Bonus Game and playoff qualification. Consumers share identical simulated PF/Potential paths.

## Scoring means

Separate regressions by observed week use YTD Potential PPG, the returning GM’s prior All-Play performance in Weeks 9–17, and prior Potential PPG in Weeks 12–14. Mean fitting uses 2021 through the preceding season. Team differences are centered on observed league YTD PPG.

The forecast-week bye adjustment holds the selected outlook’s roster fixed. Player estimates combine Week 1 Fantasy Sharks projections (two observations) and observed active-week YTD PPG. An exact legal-lineup optimizer measures each future week’s lost scoring after eligible same-roster replacements. A coefficient fitted on earlier-season forward errors converts this loss into a team mean adjustment relative to the league average loss. It uses no future-week Fantasy Sharks projections or later roster. No additional team-spread multiplier, growth factor, or separate time-of-year effect is applied.

## Matched scoring variability

Normalized 2018+ scoring history supplies the initial weekly-noise estimates. Earlier-season forward residuals from the bye-adjusted mean jointly fit one weekly SD multiplier, one persistent-strength SD multiplier and the standardized Normal-inverse-Gaussian shape. The initial persistent variance is week-specific and subtracts expected weekly noise from forward mean errors. This is the tested F315 procedure, not a new joint estimator. One persistent Normal ability offset is shared across remaining weeks; independent NIG weekly deviations are added. Weekly SD is league-wide and does not depend on team ability. Scores retain the existing nonnegative floor and one-decimal rounding.

## Data and recurring updates

For 2026: mean fitting uses 2021–2025; initial innovations use 2018–2025; bye/noise calibration uses 2022–2025. No forecast-season outcomes enter annual parameter fitting. `fit_fafl_scoring.py` regenerates prior-only fits when code or training inputs change. `forecast_byes.py` maintains selected-outlook roster/score/status snapshots and a compact forward-bye-exposure table. Weekly/correction runs refresh the latest snapshot; existing earlier outlook inputs remain fixed. No incomplete or missing bye matrix silently becomes a zero adjustment.

All consumers call `quarterly_bonus.forecast`. Unstarted quarters retain their own probabilities because forecast-week bye exposures make them non-exchangeable. The existing stochastic PF/Potential tiebreaker sampler is retained. Cutoffs remain mean simulated midpoint APW at ranks 15/16 and 17/18. Model/source revisions rebuild older outlooks with the selected week’s inputs; matching revisions preserve saved outlooks. `verify_quarterly_sync.py` checks all five Bonus Game probabilities across modules.

## Selection

F315 without extra growth was selected after the calibration and growth comparisons across 2023–2025 plus official 2026 through Week 4. Some alternatives improve pooled metrics, but none of the tested LOSO candidate-selection rules improves all four proper-score domains. That LOSO check concerns growth/candidate selection atop chronological archived engine forecasts, not entire-pipeline LOSO. Research selection is exploratory, not untouched future validation.
