import unittest

from logtriage.core import analyze_lines, normalize_message, parse_line


class ParseLineTests(unittest.TestCase):
    def test_parses_timestamp_level_and_message(self):
        entry = parse_line("2026-10-06T12:30:00Z ERROR database timeout after 5000 ms")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, "ERROR")
        self.assertEqual(entry.timestamp, "2026-10-06T12:30:00Z")
        self.assertEqual(entry.message, "database timeout after 5000 ms")

    def test_warn_is_canonicalized(self):
        entry = parse_line("[WARN] cache miss")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.level, "WARNING")

    def test_returns_none_without_level(self):
        self.assertIsNone(parse_line("plain text without a level"))


class NormalizeTests(unittest.TestCase):
    def test_replaces_volatile_values(self):
        message = (
            "request 123 from 10.0.0.8 failed id "
            "123e4567-e89b-12d3-a456-426614174000"
        )
        normalized = normalize_message(message)
        self.assertEqual(
            normalized,
            "request <num> from <ip> failed id <uuid>",
        )


class AnalyzeTests(unittest.TestCase):
    def test_groups_recurring_failures(self):
        lines = [
            "ERROR request 100 failed\n",
            "ERROR request 101 failed\n",
            "WARNING queue depth 42\n",
            "INFO started\n",
            "unstructured line\n",
        ]
        report = analyze_lines(lines)

        self.assertEqual(report["total_lines"], 5)
        self.assertEqual(report["parsed_entries"], 4)
        self.assertEqual(report["unparsed_lines"], 1)
        self.assertEqual(report["levels"]["ERROR"], 2)
        self.assertEqual(report["top_signatures"][0]["count"], 2)
        self.assertEqual(
            report["top_signatures"][0]["signature"],
            "request <num> failed",
        )

    def test_rejects_invalid_top(self):
        with self.assertRaises(ValueError):
            analyze_lines([], top=0)


if __name__ == "__main__":
    unittest.main()
