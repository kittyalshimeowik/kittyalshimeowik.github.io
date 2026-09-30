# scrapers/utilities/__tests__/test_time_utils.py
import os
import sys
import unittest
from datetime import datetime, timezone

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scrapers.utilities.time_utils import (
    format_elapsed_time,
    is_valid_unix_timestamp,
    find_timestamp_in_dict,
    parse_relative_time,
    find_relative_string_in_dict,
    parse_creation_time
)


class TestTimeUtils(unittest.TestCase):

    # -------------------------------------------------------------------------
    # 1. format_elapsed_time
    # -------------------------------------------------------------------------

    def test_format_elapsed_time_seconds_only(self):
        self.assertEqual(format_elapsed_time(0), "0s")
        self.assertEqual(format_elapsed_time(45), "45s")
        self.assertEqual(format_elapsed_time(59), "59s")

    def test_format_elapsed_time_minutes_and_seconds(self):
        self.assertEqual(format_elapsed_time(60), "1m 0s")
        self.assertEqual(format_elapsed_time(125), "2m 5s")
        self.assertEqual(format_elapsed_time(3599), "59m 59s")

    def test_format_elapsed_time_hours_minutes_and_seconds(self):
        self.assertEqual(format_elapsed_time(3600), "1h 0m 0s")
        self.assertEqual(format_elapsed_time(3665), "1h 1m 5s")
        self.assertEqual(format_elapsed_time(86400), "24h 0m 0s")

    def test_format_elapsed_time_float_conversion(self):
        self.assertEqual(format_elapsed_time(45.9), "45s")
        self.assertEqual(format_elapsed_time(125.2), "2m 5s")

    # -------------------------------------------------------------------------
    # 2. is_valid_unix_timestamp
    # -------------------------------------------------------------------------

    def test_is_valid_unix_timestamp_seconds_valid_range(self):
        valid_ts = 1700000000
        self.assertEqual(is_valid_unix_timestamp(valid_ts), valid_ts)
        # Boundaries: 2020-01-01 (1577836800) and 2030-01-01 (1893456000)
        self.assertEqual(is_valid_unix_timestamp(1577836800), 1577836800)
        self.assertEqual(is_valid_unix_timestamp(1893456000), 1893456000)

    def test_is_valid_unix_timestamp_milliseconds_conversion(self):
        # 1700000000 * 1000 = 1700000000000
        ms_ts = 1700000000123
        self.assertEqual(is_valid_unix_timestamp(ms_ts), 1700000000)

    def test_is_valid_unix_timestamp_string_digits(self):
        self.assertEqual(is_valid_unix_timestamp("1700000000"), 1700000000)
        self.assertEqual(is_valid_unix_timestamp("1700000000000"), 1700000000)

    def test_is_valid_unix_timestamp_out_of_range(self):
        # Too old (before 2020)
        self.assertIsNone(is_valid_unix_timestamp(1500000000))
        # Too far in future (after 2030)
        self.assertIsNone(is_valid_unix_timestamp(1900000000))
        # Negative timestamp
        self.assertIsNone(is_valid_unix_timestamp(-100))

    def test_is_valid_unix_timestamp_invalid_types(self):
        self.assertIsNone(is_valid_unix_timestamp(None))
        self.assertIsNone(is_valid_unix_timestamp(""))
        self.assertIsNone(is_valid_unix_timestamp("invalid_text"))
        self.assertIsNone(is_valid_unix_timestamp([]))
        self.assertIsNone(is_valid_unix_timestamp({}))

    # -------------------------------------------------------------------------
    # 3. find_timestamp_in_dict
    # -------------------------------------------------------------------------

    def test_find_timestamp_in_dict_top_level_keys(self):
        keys = ["creation_time", "publish_time", "created_time", "post_timestamp", "timestamp", "story_creation_time", "system_creation_time", "time"]
        for k in keys:
            data = {k: 1700000000}
            self.assertEqual(find_timestamp_in_dict(data), 1700000000, f"Failed for key: {k}")

    def test_find_timestamp_in_dict_deeply_nested(self):
        data = {
            "outer": {
                "middle": {
                    "inner": {
                        "creation_time": 1715000000
                    }
                }
            }
        }
        self.assertEqual(find_timestamp_in_dict(data), 1715000000)

    def test_find_timestamp_in_dict_metadata_list(self):
        data = {
            "metadata": [
                {"type": "generic"},
                {"publish_time": 1720000000}
            ]
        }
        self.assertEqual(find_timestamp_in_dict(data), 1720000000)

    def test_find_timestamp_in_dict_list_of_objects(self):
        data = [
            {"id": "node_1"},
            {"timestamp": 1718000000}
        ]
        self.assertEqual(find_timestamp_in_dict(data), 1718000000)

    def test_find_timestamp_in_dict_missing_or_invalid(self):
        self.assertIsNone(find_timestamp_in_dict({}))
        self.assertIsNone(find_timestamp_in_dict({"creation_time": "invalid"}))
        self.assertIsNone(find_timestamp_in_dict({"time": 100}))  # Out of valid range
        self.assertIsNone(find_timestamp_in_dict([]))
        self.assertIsNone(find_timestamp_in_dict(None))

    # -------------------------------------------------------------------------
    # 4. parse_relative_time
    # -------------------------------------------------------------------------

    def test_parse_relative_time_minutes_english(self):
        ref_dt = datetime(2026, 9, 30, 12, 0, 0)
        res = parse_relative_time("15 mins ago", reference_dt=ref_dt)
        self.assertIsNotNone(res)
        self.assertEqual(res["formatted"], "2026-09-30 11:45:00")

        res_singular = parse_relative_time("1 minute ago", reference_dt=ref_dt)
        self.assertIsNotNone(res_singular)
        self.assertEqual(res_singular["formatted"], "2026-09-30 11:59:00")

    def test_parse_relative_time_hours_english(self):
        ref_dt = datetime(2026, 9, 30, 12, 0, 0)
        res = parse_relative_time("3 hours ago", reference_dt=ref_dt)
        self.assertIsNotNone(res)
        self.assertEqual(res["formatted"], "2026-09-30 09:00:00")

        res_abbr = parse_relative_time("2 hr", reference_dt=ref_dt)
        self.assertIsNotNone(res_abbr)
        self.assertEqual(res_abbr["formatted"], "2026-09-30 10:00:00")

    def test_parse_relative_time_days_english(self):
        ref_dt = datetime(2026, 9, 30, 12, 0, 0)
        res = parse_relative_time("2 days ago", reference_dt=ref_dt)
        self.assertIsNotNone(res)
        self.assertEqual(res["formatted"], "2026-09-28 12:00:00")

    def test_parse_relative_time_armenian(self):
        ref_dt = datetime(2026, 9, 30, 12, 0, 0)
        # 10 րոպե առաջ (10 mins ago)
        res_min = parse_relative_time("10 րոպե առաջ", reference_dt=ref_dt)
        self.assertIsNotNone(res_min)
        self.assertEqual(res_min["formatted"], "2026-09-30 11:50:00")

        # 4 ժամ առաջ (4 hrs ago)
        res_hr = parse_relative_time("4 ժամ առաջ", reference_dt=ref_dt)
        self.assertIsNotNone(res_hr)
        self.assertEqual(res_hr["formatted"], "2026-09-30 08:00:00")

        # 3 օր առաջ (3 days ago)
        res_day = parse_relative_time("3 օր առաջ", reference_dt=ref_dt)
        self.assertIsNotNone(res_day)
        self.assertEqual(res_day["formatted"], "2026-09-27 12:00:00")

    def test_parse_relative_time_case_insensitivity(self):
        ref_dt = datetime(2026, 9, 30, 12, 0, 0)
        res = parse_relative_time("5 HOURS AGO", reference_dt=ref_dt)
        self.assertIsNotNone(res)
        self.assertEqual(res["formatted"], "2026-09-30 07:00:00")

    def test_parse_relative_time_invalid_or_none(self):
        self.assertIsNone(parse_relative_time(None))
        self.assertIsNone(parse_relative_time(""))
        self.assertIsNone(parse_relative_time("No time here"))
        self.assertIsNone(parse_relative_time("Just numbers 12345"))

    # -------------------------------------------------------------------------
    # 5. find_relative_string_in_dict
    # -------------------------------------------------------------------------

    def test_find_relative_string_in_dict(self):
        dict_text = {"text": "2 hours ago"}
        self.assertIsNotNone(find_relative_string_in_dict(dict_text))

        dict_caption = {"accessibility_caption": "3 days ago"}
        self.assertIsNotNone(find_relative_string_in_dict(dict_caption))

        dict_aria = {"aria_label": "15 mins ago"}
        self.assertIsNotNone(find_relative_string_in_dict(dict_aria))

        dict_nested = {"wrapper": {"inner": {"text": "1 hour ago"}}}
        self.assertIsNotNone(find_relative_string_in_dict(dict_nested))

        dict_none = {"wrapper": {"other": "no timestamp"}}
        self.assertIsNone(find_relative_string_in_dict(dict_none))

    # -------------------------------------------------------------------------
    # 6. parse_creation_time
    # -------------------------------------------------------------------------

    def test_parse_creation_time_valid(self):
        node = {"creation_time": 1700000000}
        res = parse_creation_time(node)
        self.assertEqual(res["timestamp"], 1700000000)
        self.assertIsNotNone(res["formatted"])

    def test_parse_creation_time_missing(self):
        node = {"random_key": "val"}
        res = parse_creation_time(node)
        self.assertIsNone(res["timestamp"])
        self.assertIsNone(res["formatted"])


if __name__ == "__main__":
    unittest.main()
