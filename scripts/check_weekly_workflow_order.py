from pathlib import Path


workflow = Path(".github/workflows/refresh.yml").read_text(encoding="utf-8")
ordered_steps = [
    "Scrape and validate the shared MFL source",
    "Build Bonus Games",
    "Publish official workbook Elo",
    "Enter and verify official Bonus Games in MFL",
    "Build playoff forecast and Game of the Week swing data",
    "Build selected Bonus Games dashboard",
    "Require synchronized quarterly forecasts before publication",
    "Build playoff bracket from official workbook Elo",
    "Confirm weekly publication and record processed scores",
]
positions = [workflow.find(f"- name: {name}") for name in ordered_steps]
if any(position < 0 for position in positions) or positions != sorted(positions):
    raise SystemExit(
        "Weekly workflow fast-publication order is invalid: "
        + " -> ".join(ordered_steps)
    )

print("Weekly workflow fast-publication order passed.")

# Retired Bonus Games sheets must not become weekly publication dependencies.
google_sync = Path("scripts/sync_google_weekly_system.py").read_text(encoding="utf-8")
legacy_bonus_ids = ("1S3NrGPEGdA3zR3-VNLLS1dAbMYFzH5rt1Z4ROoCzekU", "1X5DJD6K2mAL93DpPtHshVnOo4f_mJRc1CE2phcTFnTE")
if any(sheet_id in google_sync for sheet_id in legacy_bonus_ids):
    raise SystemExit("Weekly Google synchronization must not access retired Bonus Games sheets.")
if "python scripts/bonus_module.py --league FAFL --root . --out docs/bonus-games" not in workflow or "python scripts/verify_quarterly_sync.py --league FAFL --root ." not in workflow:
    raise SystemExit("Weekly updates must build Bonus Games and verify shared quarterly forecasts.")
print("Bonus Games module publication and legacy-sheet retirement checks passed.")
