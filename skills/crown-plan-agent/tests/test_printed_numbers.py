"""Bounded printed numeric formats, without PDF or floating-point coercion."""
import importlib.util
import sys
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))


class PrintedNumberTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("printed_numbers"),
                             "Bounded printed-number support is not implemented")
        from printed_numbers import parse_printed_amount, parse_scale_ratios
        self.amount = parse_printed_amount
        self.scales = parse_scale_ratios

    def test_plain_amounts_keep_exact_decimal_places(self):
        for text, unit, expected in (("0 ha", "ha", "0"), ("0.300 ha", "ha", "0.300"),
                                     ("150.00 m", "m", "150.00"), ("100 m2", "m2", "100")):
            with self.subTest(text=text):
                self.assertEqual(self.amount(text, unit).as_tuple(), Decimal(expected).as_tuple())

    def test_one_terminal_unit_period_is_supported(self):
        for unit in ("m", "ha", "m2"):
            with self.subTest(unit=unit):
                self.assertEqual(self.amount(f"300.00 {unit}.", unit), Decimal("300.00"))

    def test_grouping_is_validated_before_separator_removal(self):
        for text in ("1,234,567.890 ha", "1 234 567.890 ha", "1\u00a0234\u00a0567.890 ha",
                     "1\u202f234\u202f567.890 HA."):
            with self.subTest(text=text):
                self.assertEqual(self.amount(text, "ha").as_tuple(), Decimal("1234567.890").as_tuple())

    def test_square_metre_notation_has_explicit_aliases(self):
        for unit in ("m2", "m\u00b2", "m^2"):
            with self.subTest(unit=unit):
                self.assertEqual(self.amount(f"1,234.50 {unit}.", "m2"), Decimal("1234.50"))

    def test_amounts_require_the_declared_dimension(self):
        for text, unit in (("10 m2", "m"), ("10 m", "m2"), ("10 ha", "m2"),
                           ("10 m2", "ha"), ("10 m 2", "m2"), ("10 metres", "m"),
                           ("10 sq. m", "m2")):
            with self.subTest(text=text, unit=unit):
                self.assertIsNone(self.amount(text, unit))

    def test_malformed_grouping_and_decimal_comma_stay_unresolved(self):
        for number in ("1,23", "12,34,567", "1 23", "12 34 567", "1,234 567", "1 234,567",
                       "1,234,", "1,234.5,6", "0,300", "01", "01,000", "0,000", "1,,000"):
            with self.subTest(number=number):
                self.assertIsNone(self.amount(number + " ha", "ha"))

    def test_extra_content_is_never_discarded_to_find_one_amount(self):
        for text in ("300 ha..", "300 ha;", "300 ha,", "300 ha. APPROXIMATE", "ABOUT 300 ha",
                     "300 ha / 400 ha", "300 ha 400 ha", "300 ha (total)", "300. ha", ".300 ha"):
            with self.subTest(text=text):
                self.assertIsNone(self.amount(text, "ha"))

    def test_signed_exponential_and_nonfinite_numbers_stay_unresolved(self):
        for number in ("-1", "+1", "1e3", "1E+3", "NaN", "Infinity", "1_000"):
            with self.subTest(number=number):
                self.assertIsNone(self.amount(number + " m", "m"))

    def test_canonical_digit_bounds_apply_after_grouping(self):
        limit = Decimal("999999999999999999.123456789012")
        for text in ("999999999999999999.123456789012 m", "999,999,999,999,999,999.123456789012 m"):
            with self.subTest(text=text), localcontext() as context:
                context.prec = 5
                self.assertEqual(self.amount(text, "m").as_tuple(), limit.as_tuple())
        for text in ("1000000000000000000 m", "1,000,000,000,000,000,000 m", "0.1234567890123 m"):
            with self.subTest(text=text):
                self.assertIsNone(self.amount(text, "m"))

    def test_scales_accept_plain_grouped_and_terminal_period_formats(self):
        for text in ("SCALE 1:2500", "Scale 1 : 2,500", "SCALE 1:2 500", "SCALE 1:2\u00a0500",
                     "SCALE 1:2\u202f500.", "SCALE 1:2,500.", "SCALE 1:2500.", "(1:2,500) @ A3"):
            with self.subTest(text=text):
                self.assertEqual(self.scales(text), ([2500], False))

    def test_multiple_ratios_remain_separate_candidates(self):
        for text in ("MAIN 1:2,500; INSET 1:500", "1:2,500 / 1:500", "1:2,500 1:500"):
            with self.subTest(text=text):
                self.assertEqual(self.scales(text), ([2500, 500], False))
        self.assertEqual(self.scales("1:2,500; 1:2,500"), ([2500, 2500], False))

    def test_malformed_scales_never_become_valid_numeric_prefixes(self):
        for text in ("1:2,50", "1:2,500,00", "1:2,500.0", "1:2,500 000", "1:2 50",
                     "1:2500..", "1:2500,", "1:2500m", "1:2500:2", "1:2e3", "1:2_500"):
            with self.subTest(text=text):
                self.assertEqual(self.scales(text), ([], True))

    def test_numeric_continuations_across_delimiters_are_one_unsupported_candidate(self):
        for text in ("1:2500 : 2", "1:2500 / 500", "1:2500(000)", "1:2500 (000)",
                     "1:2500 [000]", "1:2500 {000}", "1:2500 / -500", "1:2500 : .2",
                     "1:2500 ( [ 000 ] )", "(1:2500) / 500"):
            with self.subTest(text=text):
                self.assertEqual(self.scales(text), ([], True))

    def test_numeric_continuation_validation_preserves_separate_ratios_and_word_notes(self):
        for text in ("1:2500 / 1:100", "1:2500 (1:100)", "(1:2500) / (1:100)"):
            with self.subTest(text=text):
                self.assertEqual(self.scales(text), ([2500, 100], False))
        for text in ("1:2500 (AT A3)", "(1:2500.) @ A3", "1:2500; MAIN VIEW"):
            with self.subTest(text=text):
                self.assertEqual(self.scales(text), ([2500], False))

    def test_unsupported_ratios_are_distinct_from_absence(self):
        for text in ("1:", "1:SCALE", "1:-2500", "1:+2500", "1:0", "1:0005", "1:01,000",
                     "2:500", "01:2500", "1.0:2500", "1e0:2500", "1:1000000001",
                     "1:99999999999999999999999999999999999999999"):
            with self.subTest(text=text):
                self.assertEqual(self.scales(text), ([], True))
        self.assertEqual(self.scales("MAIN SCALE OMITTED"), ([], False))
        self.assertEqual(self.scales("SCALE:"), ([], False))
        self.assertEqual(self.scales("1:2,500; other 2:500"), ([2500], True))

    def test_supported_scale_bounds_are_inclusive(self):
        self.assertEqual(self.scales("1:1"), ([1], False))
        self.assertEqual(self.scales("1:1,000,000,000"), ([1000000000], False))


if __name__ == "__main__":
    unittest.main()
