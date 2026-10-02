"""normalize_input acceptance/rejection matrix + shortcode math."""
import unittest

from _loader import tool
from fixtures import FAKE_CODE, FAKE_ID


class ShortcodeMathTests(unittest.TestCase):
    def test_roundtrip_known_values(self):
        self.assertEqual(tool.shortcode_to_id(FAKE_CODE), FAKE_ID)
        self.assertEqual(tool.id_to_shortcode(FAKE_ID), FAKE_CODE)

    def test_roundtrip_random_ids(self):
        import random
        random.seed(1402)
        for _ in range(50):
            n = random.randint(10**17, 10**19)
            sc = tool.id_to_shortcode(str(n))
            self.assertEqual(tool.shortcode_to_id(sc), str(n))

    def test_alien_characters_rejected(self):
        self.assertIsNone(tool.shortcode_to_id("has space"))
        self.assertIsNone(tool.shortcode_to_id(""))
        self.assertIsNone(tool.shortcode_to_id("###"))

    def test_bad_ids_rejected(self):
        self.assertIsNone(tool.id_to_shortcode("0"))
        self.assertIsNone(tool.id_to_shortcode("-5"))
        self.assertIsNone(tool.id_to_shortcode("abc"))


class NormalizeInputTests(unittest.TestCase):
    def test_full_post_url(self):
        r = tool.normalize_input(
            f"https://www.instagram.com/p/{FAKE_CODE}/?utm_source=x")
        self.assertEqual(r["shortcode"], FAKE_CODE)
        self.assertEqual(r["kind"], "post")
        self.assertEqual(r["canonical_url"],
                         f"https://www.instagram.com/p/{FAKE_CODE}/")

    def test_schemeless(self):
        r = tool.normalize_input(f"instagram.com/p/{FAKE_CODE}/")
        self.assertEqual(r["kind"], "post")

    def test_reel_variants(self):
        for path in ("reel", "reels"):
            r = tool.normalize_input(
                f"https://www.instagram.com/{path}/{FAKE_CODE}/")
            self.assertEqual(r["kind"], "reel")
            self.assertIn("/reel/", r["canonical_url"])

    def test_tv(self):
        r = tool.normalize_input(f"instagram.com/tv/{FAKE_CODE}/")
        self.assertEqual(r["kind"], "tv")

    def test_mirror_hosts(self):
        for host in ("instagr.am", "ddinstagram.com", "m.instagram.com"):
            r = tool.normalize_input(f"https://{host}/p/{FAKE_CODE}/")
            self.assertEqual(r["shortcode"], FAKE_CODE)

    def test_bare_shortcode(self):
        r = tool.normalize_input(FAKE_CODE)
        self.assertEqual(r["kind"], "bare")
        self.assertEqual(r["media_id"] if "media_id" in r else r["shortcode"],
                         FAKE_CODE)

    def test_share_link_detected(self):
        r = tool.normalize_input("https://www.instagram.com/share/AbCdEfGhI/")
        self.assertEqual(r["kind"], "share")
        self.assertTrue(r["share_path"].startswith("/share"))

    def test_rejects_whitespace(self):
        with self.assertRaises(tool.InputError) as ctx:
            tool.normalize_input("two inputs here")
        self.assertEqual(ctx.exception.code, tool.E_INVALID_INPUT)

    def test_rejects_empty(self):
        with self.assertRaises(tool.InputError):
            tool.normalize_input("")
        with self.assertRaises(tool.InputError):
            tool.normalize_input("   ")

    def test_rejects_profile_urls(self):
        with self.assertRaises(tool.InputError):
            tool.normalize_input("https://www.instagram.com/someuser/")

    def test_short_decodable_bare_token_is_accepted(self):
        # Any 5+ char alphabet token that decodes to a positive id is a
        # plausible shortcode — "hello" is honestly ambiguous, we accept.
        r = tool.normalize_input("hello")
        self.assertEqual(r["kind"], "bare")

    def test_rejects_undecodable_bare_token(self):
        with self.assertRaises(tool.InputError):
            tool.normalize_input("he!!o")

    def test_rejects_short_bare(self):
        with self.assertRaises(tool.InputError):
            tool.normalize_input("ab1")


if __name__ == "__main__":
    unittest.main()
