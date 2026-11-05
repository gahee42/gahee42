"""Run with: python3 -m unittest discover -s tests -v"""

from datetime import date, datetime, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import update_fortunes as baker


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "data" / "fortunes.json"


class DetailsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details = []
        self.summaries = 0
        self.closing_details = 0

    def handle_starttag(self, tag, attrs):
        if tag == "details":
            self.details.append(dict(attrs))
        if tag == "summary":
            self.summaries += 1

    def handle_endtag(self, tag):
        if tag == "details":
            self.closing_details += 1


class FortuneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = baker.load_fortunes(POOL)
        cls.day = date(2026, 11, 5)

    def test_pool_has_unique_messages_in_both_categories(self):
        self.assertGreaterEqual(len(self.pool), 3)
        self.assertEqual(len({item["text"] for item in self.pool}), len(self.pool))
        self.assertEqual({item["category"] for item in self.pool}, baker.CATEGORIES)

    def test_each_day_has_three_distinct_mixed_cookies_for_a_year(self):
        for offset in range(366):
            day = self.day + timedelta(days=offset)
            selected = baker.choose_daily_fortunes(self.pool, day)
            with self.subTest(day=day):
                self.assertEqual(len(selected), 3)
                self.assertEqual(len({item["id"] for item in selected}), 3)
                self.assertEqual(len({item["text"] for item in selected}), 3)
                self.assertEqual({item["category"] for item in selected}, baker.CATEGORIES)

    def test_same_day_and_namespace_are_repeatable(self):
        first = baker.choose_daily_fortunes(self.pool, self.day)
        self.assertEqual(first, baker.choose_daily_fortunes(self.pool, self.day))

    def test_reordering_pool_does_not_reroll_cookies(self):
        self.assertEqual(
            baker.choose_daily_fortunes(self.pool, self.day),
            baker.choose_daily_fortunes(list(reversed(self.pool)), self.day),
        )

    def test_daily_draws_vary_over_a_month(self):
        draws = {
            tuple(item["id"] for item in baker.choose_daily_fortunes(self.pool, self.day + timedelta(days=i)))
            for i in range(31)
        }
        self.assertGreater(len(draws), 1)

    def test_namespace_is_part_of_the_seed(self):
        with patch.object(baker.random, "Random", wraps=baker.random.Random) as rng:
            baker.choose_daily_fortunes(self.pool, self.day, "gahee42")
            first_seed = rng.call_args.args[0]
            baker.choose_daily_fortunes(self.pool, self.day, "another-profile")
            second_seed = rng.call_args.args[0]
        self.assertNotEqual(first_seed, second_seed)

    def test_render_has_exactly_three_closed_details(self):
        block = baker.render_block(baker.choose_daily_fortunes(self.pool, self.day), self.day)
        parser = DetailsParser()
        parser.feed(block)
        self.assertEqual(len(parser.details), 3)
        self.assertEqual(parser.summaries, 3)
        self.assertEqual(parser.closing_details, 3)
        self.assertTrue(all("open" not in attrs for attrs in parser.details))
        self.assertIn(self.day.isoformat(), block)

    def test_user_message_text_is_html_escaped(self):
        selected = [{"text": '<script>alert("hi")</script> & <details>'}] * 3
        block = baker.render_block(selected, self.day)
        self.assertNotIn("<script>", block)
        self.assertIn("&lt;script&gt;", block)
        self.assertIn("&amp;", block)
        self.assertEqual(block.count("<details>"), 3)

    def test_preserves_everything_outside_markers(self):
        prefix = "# Existing profile 🧑‍💻\n\nKeep this.\n"
        suffix = "\n\n## Projects\nKeep these too.\n"
        original = prefix + baker.START + "\nold\n" + baker.END + suffix
        updated = baker.replace_block(original, "new\ntext")
        self.assertEqual(updated, prefix + baker.START + "\nnew\ntext\n" + baker.END + suffix)

    def test_preserves_crlf_newlines(self):
        original = "Intro\r\n" + baker.START + "\r\nold\r\n" + baker.END + "\r\nEnd\r\n"
        result = baker.replace_block(original, "new\ntext")
        self.assertEqual(result, original.replace("old", "new\r\ntext"))

    def test_missing_duplicate_and_reversed_markers_fail(self):
        cases = [
            "# No markers", baker.START, baker.END,
            baker.START + baker.START + baker.END,
            baker.START + baker.END + baker.END,
            baker.END + baker.START,
        ]
        for content in cases:
            with self.subTest(content=content), self.assertRaises(ValueError):
                baker.replace_block(content, "new")

    def test_bad_message_pools_are_rejected(self):
        bad_pools = [
            {}, [], self.pool[:2],
            self.pool + [self.pool[0]],
            [dict(self.pool[0], id="new")] + self.pool,
            [dict(self.pool[0], text="")] + self.pool[1:],
            [dict(self.pool[0], category="other")] + self.pool[1:],
            [dict(self.pool[0], text="a\nb")] + self.pool[1:],
            [dict(self.pool[0], text=" padded ")] + self.pool[1:],
            [item for item in self.pool if item["category"] == "encouragement"],
            [42] + self.pool[1:],
            [{"id": "missing-fields"}] + self.pool[1:],
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pool.json"
            for index, pool in enumerate(bad_pools):
                path.write_text(json.dumps(pool), encoding="utf-8")
                with self.subTest(case=index), self.assertRaises(ValueError):
                    baker.load_fortunes(path)

    def test_invalid_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pool.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                baker.load_fortunes(path)

    def test_date_validation(self):
        self.assertEqual(baker.parse_date("2028-02-29"), date(2028, 2, 29))
        for bad in ("2026-02-29", "2026-13-01", "20261105", "2026-1-5", "tomorrow"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                baker.parse_date(bad)

    def test_kst_date_and_offset(self):
        self.assertEqual(baker.KST.utcoffset(None), timedelta(hours=9))
        with patch.object(baker, "datetime") as mocked:
            mocked.now.return_value = datetime(2026, 11, 5, 0, 1, tzinfo=baker.KST)
            self.assertEqual(baker.today_kst(), date(2026, 11, 5))
            mocked.now.assert_called_once_with(baker.KST)

    def test_update_is_idempotent_and_preserves_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "README.md"
            path.write_text("Before\n" + baker.START + "\nold\n" + baker.END + "\nAfter\n", encoding="utf-8")
            self.assertTrue(baker.update_readme(path, POOL, self.day, "gahee42"))
            first = path.read_bytes()
            self.assertFalse(baker.update_readme(path, POOL, self.day, "gahee42"))
            self.assertEqual(first, path.read_bytes())
            self.assertTrue(path.read_text(encoding="utf-8").startswith("Before\n"))
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\nAfter\n"))
            self.assertTrue(baker.update_readme(path, POOL, self.day + timedelta(days=1), "gahee42"))

    def test_cli_runs_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "README.md"
            path.write_text(baker.START + "\n" + baker.END + "\n", encoding="utf-8")
            command = [sys.executable, str(ROOT / "scripts/update_fortunes.py"), "--readme", str(path), "--date", "2026-11-05"]
            first = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            second = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("Updated", first.stdout)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("Already current", second.stdout)

    def test_cli_failure_does_not_touch_readme(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "README.md"
            original = b"# A profile without markers\n"
            path.write_bytes(original)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/update_fortunes.py"), "--readme", str(path)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("exactly one START marker", result.stderr)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
