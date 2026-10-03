# FAFL GM career history

Completed-season history: 2014–2025, 384 team-seasons. The historical files are
used only for career results. `current_gms_2026.json` is the required 2026
ownership input; the renderer joins history to it by GM rather than assuming a
2025 franchise still has the same owner.
Careers follow each manager across FAFL franchises, never across leagues.
Christian Lohr is treated as sole manager; co-owners are ignored. Jonathan Bell
receives his shared New England 2021 season. Unchanged co-manager groups count
shared seasons once. Experience counts completed seasons. Career all-play rank
uses (wins + 0.5 * ties) / games among the 32 current teams.

Full-season all-play uses actual weekly MFL scores, including bye/unscheduled
teams: 16 weeks through 2020, 17 thereafter. Each team has 31 comparisons per
week. The renderer adds current-season games from the existing shared snapshot,
including postseason games after the qualifying picture freezes.

Finish order is playoff finish (12 teams through 2019, 14 thereafter), then the
two consolation champions ordered by full-season all-play, then remaining teams
by full-season all-play. Total points break equal all-play records. Final-week
Bragging Rights games distinguish equal conference finishes.

User-confirmed historical corrections/reconstructions:
- 2018: Week 16 all-play inputs were potential points in error. The source sheet
  now uses actual points. NEP won the AFC ladder 176.5–169.7 over OAK; the payouts
  source has also been corrected to NEP.
- 2018: MIN won its two-week fifth-place series over LAR. Correct Bragging Rights
  pairings are reconstructed with actual Week 16 scores: NYJ 170.2 over MIN 169.0
  (overall 9th/10th), LAR 182.4 over BAL 161.2 (11th/12th).
- 2022: Missing Bragging Rights matchups are reconstructed by matching equal
  conference finishes and comparing actual Week 17 scores. These are historical
  reconstructions, not claims that MFL scheduled those games.

Sources: archived league pages, payout sheets, MFL schedule and weeklyResults
exports with W=YTD&MISSING_AS_BYE=1. League IDs: 2014 37677, 2015 27312,
2016 onward 22686. Sheet URLs are in gm_career_sources.json. Only public manager
names and league results are retained, with no private contact details.

Create the season-specific ownership file for each new season and update it for
ownership changes. The runtime rejects a missing or wrong-season file rather
than silently falling back to a completed-season roster.
