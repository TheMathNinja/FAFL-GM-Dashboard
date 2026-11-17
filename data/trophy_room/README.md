# FAFL Trophy Room









The module and Playoff Picture use `data/gm_career_seasons.json` as the single authoritative completed-season GM history. Current ownership comes from `current_gms_2026.json`. Alias and punctuation matching follows `scripts/gm_profiles.py`. Identical lifetime co-ownership stints appear together and shared seasons count once.














`payouts.json` imports the 2014–2017 local AFL workbooks and 2018–2025 Google Sheets listed in `gm_career_sources.json`. AFL is FAFL's former name. Prize totals reconcile with raw prize earnings and exclude deposit/payment adjustments. File hashes preserve provenance. The 2018 AFC ladder prize goes to NEP ($90), not OAK ($0), using the corrected source once.









Records are finalized MFL league standings including league bonus results. The historical MFL league IDs are 37677 (2014), 27312 (2015), and 22686 (2016 onward). Through 2022, FAFL's NFC West IDs were SFO 0014, SEA 0015, LAR 0016. They changed in 2023 to LAR 0014, SFO 0015, SEA 0016. Historical joins respect the ID mapping in each season.









Rebuild the displayed data with `python scripts/build_trophy_room.py`; validate with `python -m unittest discover -s tests -p test_trophy_room.py`. Refresh archived inputs and advance canonical completed-season history together when a new season completes; coverage updates automatically.









## Results source policy









Trophy Room does not read the retired Trophy Room workbook or CSV. Both leagues use season-specific MFL weekly results (the same results published on the MFL league pages). `scripts/import_trophy_results.py` imports Super Bowl finals, starting lineups and regular-season award metrics together. `champions.json` and `super_bowl_lineups.json` are validated against each other at build time; the importer also reconciles full-season and regular-season all-play against every canonical team-season row used by GM profiles. Any disagreement stops the import.









Official results use MFL's stored franchise score, not an independently substituted player sum. In ADL 2022, MFL retains 208.0-198.6 while current starter points sum to 221.0-204.4 after documented Bills/Bengals replacement imports. Both values are explicitly distinguished in the hover; no synthetic adjustment is added to players. ADL 2025 is 248.9-207.2 in both MFL matchup results and starter sums.









Conference award recipients remain those recorded in the published payout workbooks (including the early local workbooks). Metrics are calculated from MFL weeks 1-12: HC is league-wide all-play percentage, OC/DC sum actual offensive/defensive starters, and GM sums MFL optimal starters (`shouldStart=1`), matching the shared weekly dashboard calculation. Decimal values round half up at display precision. Earnings and historical payout corrections use their existing audited sources; no earnings come from the retired Trophy Room.









Refresh after historical scoring corrections or when a completed season is added:









```




python scripts/import_trophy_results.py --league LEAGUE --cache /path/to/mfl-cache




```









Replace LEAGUE with ADL or FAFL, then run the ordinary Trophy Room builder. A fresh cache fetches current MFL exports; an existing cache reproduces its exact responses. `results_provenance.json` records source URLs and SHA-256 hashes. The old `import_super_bowl_lineups.py` entry point delegates to this importer, so it cannot reintroduce a different final from displayed data.








## Ending-roster player statistics







Yearly Results team names and logos open the championship-week MFL roster, including IR and taxi players. `python scripts/import_trophy_rosters.py --league LEAGUE --cache /path/to/mfl-cache` refreshes every completed season. Raw responses can be reproduced with that cache; source URLs and SHA-256 hashes are stored in `rosters_provenance.json`. Both ordinary builders validate season coverage and copy the imported snapshots to the website. The UI fetches only the selected year's roster file when needed.







Player statistics cover weeks 1 through the fantasy championship (Week 16 before 2021, Week 17 thereafter), irrespective of the fantasy franchise holding the player at the time. MFL's Top Performers weekly report supplies points and played-game presence. Numeric zero-point games count toward GP; byes and absent games do not. PPG is total points / GP. Starter points sum the weeks in which the player played and any franchise in the league started him. Starter PPG divides by those games started; duplicate player copies count once per week. No starts displays zero starter points and an unavailable starter average. Negative points remain negative. Older MFL roster exports sometimes duplicate a taxi player as an active player; roster membership is deduplicated by player ID, preserving the reserve designation.







The importer checks every scored starter against the same MFL weekly player report before publishing. Tests cover trades between franchises, duplicate copies, zero-point games, missed games, negative scores, zero starts, reserve duplication and full historical coverage. Run `python -m unittest discover -s tests -p test_trophy_rosters.py` after importing.






## Top Performances





The fourth view is ordered Hall of Fame, Yearly Results, Top Performances, All-Time GM Stats. Native Scoring and Current Scoring cover Total Team Points, Offensive Points (including PK/PN and historical KR), Defensive Points, Potential Points, and individual player games by position. Team lists separate NFC/AFC and Weeks 1-12/playoffs. Higher points rank first; ties at tenth are retained. Individual player games are unique by year/week/MFL player ID, regardless of fantasy copies or whether anyone started the player.





Native results come from season-specific MFL weekly results and the public Top Performers report. Player metadata requests include the league ID to preserve historical league-specific position overrides. Historical franchise/GM identities follow the same canonical career history and alias helpers as the other Trophy Room views. Playoff fields use the published six/seven-team bracket format and audited finishes; scheduled field/placement games count, byes and consolation teams do not. Once the current regular season finishes, qualification comes from the existing published bracket-data snapshot, never projected qualifiers.





Current Scoring uses the existing ADL26 reconstructed NFL-stat overlay for earlier seasons and recorded MFL scores for 2026. It is explicitly labeled reconstructed, not an original MFL result or a fitted forecasting model. Original starters and historical positional limits are preserved; Potential Points is reoptimized within those limits. Missing player scores and positions absent from 2026 scoring (notably FAFL's historical KR slot) are excluded, never silently assigned zero. The UI displays coverage for the selected metric. MFL stored totals remain distinct from player sums where necessary. Player/team popups show stat lines or the applicable lineup and link to the original public MFL scoring report.





`top_performances_history.json` freezes completed-season top ranks and their detail records. `top-performances.json` merges those with all completed current-season weeks; it is the source for the identical website snapshot. Source URLs/hashes, the scoring-rule fingerprint, overlay hash and statistical-source provenance are retained in these snapshots and `top_performances_sources.json`. Historical football stat lines use the audited season-specific GSIS/MFL maps; 2022 BUF/CIN replacement statistics use Week 18 consistently with the league imports. Current-season supplemental stat lines use nflverse and DynastyProcess ID mappings. Scoring-page links show original MFL points, not the reconstructed counterfactual.





Refresh only the completed current-season weeks:





```


python scripts/import_top_performances.py --league LEAGUE --cache artifacts/top-performance-cache


python -m unittest discover -s tests -p test_top_performances.py


```





Replace LEAGUE with ADL or FAFL. The existing authorized weekly publication workflow runs this after its publication marker. A failed optional records refresh preserves the last successful dated snapshot and does not block core league publication. Ordinary Trophy Room builds copy the saved snapshot. The updater refuses to silently advance the Current Scoring year or accept a changed rule fingerprint: rebuild/audit historical reconstruction when scoring changes.





To rebuild completed-season rankings, supply the original derived scoring CSV and optional stat lines generated from the existing local NFL caches:





```


Rscript scripts/export_performance_stat_lines.R FFAUC_ROOT artifacts/performance-stat-lines.json


python scripts/import_top_performances.py --league LEAGUE --history --overlay PATH_TO_ADL26_OVERLAY_CSV --stats artifacts/performance-stat-lines.json --cache artifacts/historical-performance-cache


python scripts/import_top_performances.py --league LEAGUE --cache artifacts/current-performance-cache


```





The overlay source is `DerivedScoringData/ff_playerscores_FAFL_withADL26scores_2014_2025.csv`, produced by the existing `HelperFunctions/build_ff_playerscores_with_adl26_scores.R` / `add_estimated_fafl_pts.R` pipeline. It is not the retired Trophy Room workbook. Neither importer modifies the original league caches. Rebuild completed history after historical source corrections; rebuild the 2026 reconstruction before deliberately advancing the scoring-year guard. The stat-line exporter requires R's jsonlite package; runtime importers/tests use Python's standard library and the existing shared Trophy Room helpers.




### Player scoring-event popups



Player popups follow CHI Team Tools: Event / Points rows, position-specific event order, per-event rounding, and a Total footer. `scripts/performance_scoring.py` evaluates captured MFL `live_stats_idp_WW.txt` events against that league's season-specific rules for Native Scoring and 2026 rules for recorded current-season games. Labels and ordering use the same MFL event catalog as CHI Team Tools, extended with missing official MFL allRules labels. Historical source availability is recorded honestly: missing native event details show the published total with an explicit reference-only note. If captured events disagree with MFL's stored total, both are shown; the ranking retains the published total without inventing an adjustment.



Historical Current Scoring uses the frozen `top_performances_reconstructed_breakdowns.json` contribution bank from the existing ADL26 overlay engine (`add_estimated_fafl_pts.R`, `keep_details=TRUE`) and original cached NFL statistics. Every retained Current Scoring contribution sum is checked against its ranked estimate. These are labeled reconstructed; they are not represented as original MFL event records. Return yards with no scoring rule never appear as scoring contributions. The bank retains engine/cache file hashes. Rebuild it alongside the historical scoring overlay when historical inputs change: `Rscript scripts/export_performance_scoring_breakdowns.R FFAUC_ROOT`. The exporter loads function definitions only and never initializes league connections or changes source caches. Ordinary refreshes retain saved historical breakdowns and fetch completed current-season event sources; they do not run R or read local NFL caches. The snapshots remain identical between source and docs. `tests/test_performance_scoring.py` covers unscored return yards, per-event rounding/field-goal thresholds, all saved sums, and Taysom Hill's 2022 Week 5 47.8-point result.


Individual Performances retains the top 25 unique NFL player games for every supported position in Native Scoring and Current Scoring, including all ties at rank 25. Team boards remain top 10 including ties at tenth. The expanded historical snapshots and reconstructed contribution bank include the additional games; completed current-season weeks merge with these using the same separate limits. The source metadata records `individualRankingLimit: 25` and `teamRankingLimit: 10`.

### Top Seasonlong Scores

The seasonlong tab ranks team seasons (top 10 including ties) by record winning percentage, all-play percentage, total, offensive, defensive, or potential points, separately for NFC/AFC. Individual NFL player seasons retain the top 25 including ties at each position. Team and individual Regular Season / Playoffs / Combined selectors are independent. Regular season covers Weeks 1–12; team playoffs use actual qualifying teams and scheduled postseason games, including placement games, excluding byes and consolation teams. Partial current-season entries are labeled. H2H uses the MFL schedule; all-play and points count each team-week once. Popups reconcile weekly totals and link to original MFL reports.

Native Scoring preserves MFL scores and audited records. Current Scoring uses the same reconstructed historical overlay and lineup optimizer as Top Weekly Scores; missing required inputs exclude a total rather than silently treating it as zero. Offensive points include special teams. Current-season games use recorded scores and results. Canonical GM membership comes from gm_career_seasons.json and the current roster, with input hashes retained in metadata.

Both leagues use four quarterly bonuses through 2020 and five bonuses from 2021 (four quarters plus the regular season). Bonus rankings use league-wide all-play, points, then potential points; award cutoffs are within conferences through 2024 and league-wide from 2025. See the [2021 schedule proposals](https://www46.myfantasyleague.com/2021/options?L=60206&O=28&THREAD=39) and [2023 ballot discussion](https://www46.myfantasyleague.com/2023/options?L=60206&O=28&THREAD=25), which describes five bonuses. FAFL 2023 published totals include one extra result for every team matching Q4. No sixth-bonus authorization was found. Native preserves this as a separately labeled MFL adjustment; reconstructed Current Scoring applies the standard five. This importer does not alter canonical GM history or MFL standings.

Build completed history with `python scripts/import_seasonlong_performances.py --league LEAGUE --history --overlay PATH_TO_ADL26_OVERLAY_CSV --cache CACHE`. Ordinary refreshes run the same command without --history/--overlay and merge current completed weeks with the frozen seasonlong_performances_history.json. Rebuild history when historical sources change. Builders copy the snapshot to docs; the optional official-write-authorized workflow step refreshes it alongside weekly rankings. Tests verify rank ties, bonus formats, saved total reconciliation, and native canonical records.
