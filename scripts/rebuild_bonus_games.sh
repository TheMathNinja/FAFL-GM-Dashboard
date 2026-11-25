#!/usr/bin/env bash
set -euo pipefail

python -m unittest discover -s tests -p test_exact_clinching.py -v
python scripts/fit_fafl_scoring.py --root . --all-seasons
python -m unittest discover -s tests -p test_selected_uncertainty.py -v
python -m unittest discover -s tests -p test_scoring_engine.py -v
python -m unittest discover -s tests -p test_forecast_byes.py -v
python -m unittest discover -s tests -p test_weekly_pairs.py -v
python -m unittest discover -s tests -p test_upcoming_sharks.py -v
python -m unittest discover -s tests -p test_player_availability.py -v
python -m unittest discover -s tests -p test_bonus_predictor.py -v
python -m unittest discover -s tests -p test_shared_quarterly.py -v
python scripts/forecast_byes.py --root . --refresh-current
python scripts/build.py --stage playoff
python -m unittest discover -s tests -p test_bonus_outlook_archive.py -v
python scripts/bonus_module.py --league FAFL --root . --out docs/bonus-games --simulations 12000
python scripts/verify_quarterly_sync.py --league FAFL --root .
