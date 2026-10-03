# FAFL Trophy Room

The module and Playoff Picture use `data/gm_career_seasons.json` as the single authoritative completed-season GM history. Current ownership comes from `current_gms_2026.json`. Alias and punctuation matching follows `scripts/gm_profiles.py`. Identical lifetime co-ownership stints appear together and shared seasons count once.

`champions.json` preserves champions and actual final-week scores from archived MFL games; published payout recipients determine annual awards. OC/DC metrics were independently summed from actual regular-season starters (weeks 1–12), and GM potential PPG from the MFL weekly results. HC uses regular-season all-play. General Manager awards were not awarded in 2014; the cards say Not awarded and no winner is counted for that season rather than inventing a winner.

`payouts.json` imports the 2014–2017 local AFL workbooks and 2018–2025 Google Sheets listed in `gm_career_sources.json`. AFL is FAFL's former name. Prize totals reconcile with raw prize earnings and exclude deposit/payment adjustments. File hashes preserve provenance. The 2018 AFC ladder prize goes to NEP ($90), not OAK ($0), using the corrected source once.

Records are finalized MFL league standings including league bonus results. The historical MFL league IDs are 37677 (2014), 27312 (2015), and 22686 (2016 onward). FAFL's NFC West IDs are SFO 0014, SEA 0015, LAR 0016, which differ from ADL.

Rebuild the displayed data with `python scripts/build_trophy_room.py`; validate with `python -m unittest discover -s tests -p test_trophy_room.py`. Refresh archived inputs and advance canonical completed-season history together when a new season completes; coverage updates automatically.

