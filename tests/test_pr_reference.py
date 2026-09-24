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
        """Reject a repository reference with no owner/name separator."""
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner", "1")

    def test_repo_extra_slashes(self):
        """Reject a repository reference with more than one separator."""
        with self.assertRaises(InvalidPrReferenceError):
            PRReference.from_parts("owner/repo/extra", "1")

    def test_repo_split_preserves_valid_component_boundaries(self):
        """Keep valid owner and repository components intact after splitting."""
        cases = (
            ("a/b", "a", "b"),
            ("Org-1/Repo_2", "Org-1", "Repo_2"),
            ("a.b_c/d.e-f", "a.b_c", "d.e-f"),
            ("  Owner/Repo  ", "Owner", "Repo"),
        )
        for repo, owner, name in cases:
            with self.subTest(repo=repo):
                ref = PRReference.from_parts(repo, "7")
                self.assertEqual((ref.owner, ref.name), (owner, name))
                self.assertEqual(parse_repo_name(repo), f"{owner}/{name}")

    def test_repo_split_requires_exactly_one_slash(self):
        """Report the slash count when a reference has extra or missing separators."""
        cases = (
            ("owner", 0),
            ("owner/repo/extra", 2),
            ("owner//repo", 2),
            ("/owner/repo", 2),
            ("owner/repo//extra", 3),
        )
        for repo, slash_count in cases:
            with self.subTest(repo=repo):
                with self.assertRaisesRegex(
                    InvalidPrReferenceError,
                    rf"repo must be exactly owner/name \(got {slash_count} '/'\)",
                ):
                    PRReference.from_parts(repo, "7")

    def test_repo_split_rejects_empty_components(self):
        """Reject empty owner and repository names after splitting."""
        cases = (("/repo", "owner is empty"), ("owner/", "repo name is empty"))
        for repo, message in cases:
            with self.subTest(repo=repo):
                with self.assertRaisesRegex(InvalidPrReferenceError, message):
                    PRReference.from_parts(repo, "7")

    def test_repo_split_validates_each_component(self):
        """Reject invalid characters in either repository component."""
        cases = (
            ("owner./repo", "owner contains invalid characters"),
            ("owner/repo_", "repo name contains invalid characters"),
            ("owner/rep:o", "repo name contains invalid characters"),
            ("own\x7fer/repo", "repo reference contains whitespace/control characters"),
            ("owner/na me", "repo reference contains whitespace/control characters"),
        )
        for repo, message in cases:
            with self.subTest(repo=repo):
                with self.assertRaisesRegex(InvalidPrReferenceError, message):
                    PRReference.from_parts(repo, "7")

    def test_repo_split_shared_by_reference_entry_points(self):
        """Apply the same splitting rules through every public parser entry point."""
        ref = PRReference.from_string("Org-1/Repo_2#7")
        self.assertEqual((ref.owner, ref.name), ("Org-1", "Repo_2"))
        self.assertEqual(parse_pr_reference("  Org-1/Repo_2  ", "7"), ref)
        with self.assertRaisesRegex(
            InvalidPrReferenceError, r"repo must be exactly owner/name \(got 2 '/'\)"
        ):
            PRReference.from_string("owner//repo#7")
        with self.assertRaisesRegex(
            InvalidPrReferenceError,
            r"tasks/test.md:3: repo must be exactly owner/name \(got 2 '/'\)",
        ):
            parse_pr_reference(
                "owner//repo", "7", loc=("tasks/test.md", 3), strict=True
            )

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
            result = parse_repo_name("bad-name", loc=("tasks/test.md", 3))
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
