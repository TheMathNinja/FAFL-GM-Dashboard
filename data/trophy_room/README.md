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
