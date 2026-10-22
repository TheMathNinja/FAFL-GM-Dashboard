import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_quarterly_sync import verify_snapshot


class QuarterlySyncTests(unittest.TestCase):
    def test_accepts_dashboard_precision_rounding(self):
        bonus = {
            "weeks": {
                "1": [{
                    "id": "0003",
                    "events": [{
                        "event": "Q4",
                        "completed": False,
                        "credit": 0.7009583333333333,
                    }],
                }],
            },
        }
        playoff = {
            "NFC": [{
                "franchise_id": "0003",
                "winDetails": {
                    "bonusGames": [{"label": "Q4 Bonus Game", "probability": 0.701}],
                },
                "actualDetails": {"bonusGames": []},
            }],
            "AFC": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "week-02.html"
            page.write_text("const data = " + json.dumps(playoff), encoding="utf8")
            self.assertEqual(verify_snapshot(root, "FAFL", bonus, 1, page.name), 1)


if __name__ == "__main__":
    unittest.main()
