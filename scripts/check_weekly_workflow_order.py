from pathlib import Path


workflow = Path(".github/workflows/refresh.yml").read_text(encoding="utf-8")
ordered_steps = [
    "Scrape and validate the shared MFL source",
    "Build Bonus Games",
    "Publish official workbook Elo and synchronize Bonus Games inputs",
    "Enter and verify official Bonus Games in MFL",
    "Build playoff forecast and Game of the Week swing data",
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
