import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from app import (
    last_six_months,
    money,
    parse_amount,
    parse_record_date,
    record_created_at,
    sort_by_added,
    summary_period_matches,
    transaction_date,
)


class CalculationAndOrderingTests(unittest.TestCase):
    def test_amounts_are_normalized_to_two_decimals(self):
        self.assertEqual(parse_amount("1,234.567"), Decimal("1234.57"))
        self.assertEqual(money(1234.567), Decimal("1234.57"))
        self.assertEqual(money("bad"), Decimal("0.00"))

    def test_invalid_amount_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_amount("0")
        with self.assertRaises(ValueError):
            parse_amount("not-a-number")

    def test_record_date_parsing(self):
        self.assertEqual(parse_record_date("2026-09-07"), date(2026, 9, 7))
        self.assertEqual(transaction_date({"date": "2026-09-07"}), date(2026, 9, 7))

    def test_added_order_is_newest_first_and_uses_object_id_fallback(self):
        older = {"_id": "000000000000000000000001", "created_at": datetime(2026, 9, 1, tzinfo=timezone.utc)}
        newer = {"_id": "000000000000000000000002", "created_at": datetime(2026, 9, 2, tzinfo=timezone.utc)}
        result = sort_by_added([older, newer])
        self.assertIs(result[0], newer)
        self.assertIs(result[1], older)

    def test_created_at_fallback_is_timezone_aware(self):
        value = record_created_at({})
        self.assertEqual(value.tzinfo, timezone.utc)

    def test_summary_period_boundaries(self):
        today = date(2026, 9, 7)
        self.assertTrue(summary_period_matches(date(2026, 9, 7), "weekly", "", "", "", today))
        self.assertTrue(summary_period_matches(date(2026, 9, 1), "weekly", "", "", "", today))
        self.assertFalse(summary_period_matches(date(2026, 8, 31), "weekly", "", "", "", today))
        self.assertTrue(summary_period_matches(date(2026, 9, 1), "monthly", "", "", "", today))
        self.assertFalse(summary_period_matches(date(2026, 8, 31), "monthly", "", "", "", today))
        self.assertTrue(summary_period_matches(date(2026, 9, 7), "daily", "2026-09-07", "", "", today))
        self.assertFalse(summary_period_matches(date(2026, 9, 6), "daily", "2026-09-07", "", "", today))
        self.assertTrue(summary_period_matches(date(2026, 9, 5), "range", "", "2026-09-01", "2026-09-05", today))
        self.assertFalse(summary_period_matches(date(2026, 9, 6), "range", "", "2026-09-01", "2026-09-05", today))

    def test_last_six_months_returns_current_month_and_five_previous(self):
        months = last_six_months(date(2026, 9, 7))
        self.assertEqual(len(months), 6)
        self.assertEqual(months[0][:2], (2026, 4))
        self.assertEqual(months[-1][:2], (2026, 9))
        self.assertEqual(months[0][2], "Apr 2026")
        self.assertEqual(months[-1][2], "Sep 2026")


if __name__ == "__main__":
    unittest.main()
