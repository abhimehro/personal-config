import io
import sys
import unittest

sys.path.insert(0, "/".join(__file__.split("/")[:-2]))

from pr_reference import (
    InvalidPrReferenceError,
    PRReference,
    parse_pr_reference,
    parse_repo_name,
)


class TestPRReference(unittest.TestCase):
    def test_from_parts(self):
        ref = PRReference.from_parts("  abhimehro/personal-config  ", "  123  ")
        self.assertEqual(ref.owner, "abhimehro")
        self.assertEqual(ref.name, "personal-config")
        self.assertEqual(ref.number, 123)
        self.assertEqual(ref.repo, "abhimehro/personal-config")
        self.assertEqual(ref.full, "abhimehro/personal-config#123")

    def test_from_string(self):
        ref = PRReference.from_string("owner/repo#42")
        self.assertEqual(ref.repo, "owner/repo")
        self.assertEqual(ref.number, 42)

    def test_repo_missing_slash(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner", "1")

    def test_repo_extra_slashes(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo/extra", "1")

    def test_repo_leading_hyphen(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("-owner/repo", "1")

    def test_repo_name_leading_hyphen(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/-repo", "1")

    def test_repo_whitespace(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner /repo", "1")

    def test_repo_control_character(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/re\x00po", "1")

    def test_pr_zero(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo", "0")

    def test_pr_negative(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo", "-1")

    def test_pr_non_decimal(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo", "abc")

    def test_pr_leading_zero(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo", "0123")

    def test_pr_leading_hyphen(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo", "-123")

    def test_pr_shell_metacharacters(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo", "123; touch /tmp/pwned")

    def test_repo_shell_metacharacters(self):
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo$(touch /tmp/pwned)", "1")

    def test_parse_repo_name_valid(self):
        self.assertEqual(parse_repo_name("owner/repo"), "owner/repo")

    def test_parse_repo_name_non_strict_skips_invalid(self):
        captured = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured
        try:
            result = parse_repo_name("bad-name", source="tasks/test.md", line=3)
        finally:
            sys.stderr = old_stderr
        self.assertIsNone(result)
        self.assertIn("skipping invalid repo name", captured.getvalue())
        self.assertIn("tasks/test.md:3", captured.getvalue())

    def test_parse_repo_name_strict_raises(self):
        with self.assertRaises(InvalidPrReferenceError):
            parse_repo_name("bad-name", strict=True)

    def test_parse_pr_reference_non_strict(self):
        self.assertIsNone(parse_pr_reference("owner", "abc"))

    def test_parse_pr_reference_strict(self):
        with self.assertRaises(InvalidPrReferenceError):
            parse_pr_reference("owner", "abc", strict=True)


if __name__ == "__main__":
    unittest.main()
