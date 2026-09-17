# FAFL GM Dashboard

A separate GM suite for Football Analytics Fantasy Lab. The first module is Playoff Picture.

## Rebuild

Python 3.12+:

```
pip install -r requirements.txt
python -m unittest discover -s tests
python scripts/build.py --status reported
```

MFL league 22686 supplies current scores and lineups. One weeklyResults response supplies both the model and point breakdowns. No MFL credentials are needed. GitHub Actions runs Tuesday 1 a.m. and Thursday 5 a.m. America/New_York, with paired UTC cron slots and a DST gate. Actions can start late.

## Model

Two separate regressions predict remaining actual and potential PPG from current Potential PPG, the returning GM's prior All-Play percentage in Weeks 9-17, and prior Potential PPG in Weeks 12-14. Earlier completed seasons train each forecast. Missing history uses training-sample means. Public predecessor tables contain franchise IDs only; no owner contact data is stored.

Four division winners and three wildcards qualify per conference. Seeds follow All-Play, actual points and Potential Points. Division H2H uses a mini-league of the tied teams. All-Play covers all 32 teams. Potential Points break bonus-game ties after All-Play and actual points.

Historical scores retain their original scoring rules. This is the user-approved historical model, not a historical rescore under 2026 rules. Current 2026 inputs come directly from MFL. See docs/model.html for performance and limitations.

## Annual rollover

The repository targets 2026. Before changing SEASON and the workflow year, add the completed season to historical_weekly.csv, match returning GMs privately, export only the new ID mapping, and rerun validation. Do not match GM history merely by retaining the franchise ID.

## Deployment

GitHub Pages uses Actions to serve docs/. Scheduled and manual runs build and deploy the same artifact. Concurrent runs are serialized. Failed validation stops publication and preserves the previous live report. Weekly CSV and HTML archives are retained; official corrections replace the corresponding week's snapshot.
