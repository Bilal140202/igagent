"""Decode-slot parsers against synthetic HTML/JSON (no network)."""
import unittest
from unittest import mock

from _loader import tool
from fixtures import (FAKE_CODE, FAKE_ID, CDN_JPEG, CDN_MP4, CDN_WEBP,
                      rich_embed_html, ssr_embed_html, ssr_unavailable_html,
                      og_meta_html, og_video_html)


class EmbedJsonSlotTests(unittest.TestCase):
    def test_shape_a_rich_payload(self):
        html = rich_embed_html()
        with mock.patch.object(tool, "http_get", return_value=html.encode()):
            outcome, post = tool._fetch_embed_json(FAKE_CODE, "post")
        self.assertEqual(outcome, "ok")
        self.assertEqual(post["shortcode"], FAKE_CODE)
        self.assertEqual(post["media_id"], FAKE_ID)
        self.assertEqual(post["type"], "carousel")
        self.assertEqual(len(post["media_items"]), 3)
        kinds = [i["type"] for i in post["media_items"]]
        self.assertEqual(kinds, ["image", "video", "image"])
        self.assertEqual(post["media_items"][1]["url"], CDN_MP4)
        self.assertEqual(post["author"]["username"], "synthetic_user")
        self.assertTrue(post["author"]["verified"])
        self.assertEqual(post["like_count"], 3456)
        self.assertEqual(post["caption"], "synthetic caption")
        self.assertEqual(post["extraction_source"], "embed_json")

    def test_unavailable_page(self):
        with mock.patch.object(tool, "http_get",
                               return_value=ssr_unavailable_html().encode()):
            outcome, _ = tool._fetch_embed_json(FAKE_CODE, "post")
        self.assertEqual(outcome, "unavailable")

    def test_shell_page_falls_through(self):
        with mock.patch.object(tool, "http_get",
                               return_value=b"<html><body>shell</body></html>"):
            outcome, post = tool._fetch_embed_json(FAKE_CODE, "post")
        self.assertEqual(outcome, "failed")
        self.assertIsNone(post)

    def test_http_404_is_unavailable(self):
        import urllib.error
        err = urllib.error.HTTPError("url", 404, "nf", {}, None)
        with mock.patch.object(tool, "http_get", side_effect=err):
            outcome, _ = tool._fetch_embed_json(FAKE_CODE, "post")
        self.assertEqual(outcome, "unavailable")


class EmbedHtmlSlotTests(unittest.TestCase):
    def test_ssr_image_post(self):
        with mock.patch.object(tool, "http_get",
                               return_value=ssr_embed_html().encode()):
            outcome, post = tool._fetch_embed_html(FAKE_CODE, "post")
        self.assertEqual(outcome, "ok")
        self.assertEqual(post["author"]["username"], "synthetic_user")
        self.assertEqual(post["author"]["followers"], 12300)
        self.assertEqual(len(post["media_items"]), 1)
        img = post["media_items"][0]
        self.assertEqual(img["type"], "image")
        self.assertEqual(img["url"], CDN_JPEG)
        self.assertEqual(post["media_id"], FAKE_ID)
        self.assertIsNone(post["caption"])  # not exposed at this tier

    def test_unavailable(self):
        with mock.patch.object(tool, "http_get",
                               return_value=ssr_unavailable_html().encode()):
            outcome, _ = tool._fetch_embed_html(FAKE_CODE, "post")
        self.assertEqual(outcome, "unavailable")

    def test_no_media_is_failure(self):
        with mock.patch.object(tool, "http_get",
                               return_value=b"<html><body></body></html>"):
            outcome, _ = tool._fetch_embed_html(FAKE_CODE, "post")
        self.assertEqual(outcome, "failed")


class OgMetaSlotTests(unittest.TestCase):
    def test_og_image_post(self):
        with mock.patch.object(tool, "http_get",
                               return_value=og_meta_html().encode()):
            outcome, post = tool._fetch_og_meta(FAKE_CODE, "post")
        self.assertEqual(outcome, "ok")
        self.assertEqual(post["author"]["username"], "synthetic_user")
        self.assertEqual(post["caption"], "synthetic og caption here")
        self.assertEqual(post["media_items"][0]["url"], CDN_JPEG)
        self.assertEqual(post["extraction_source"], "og_meta")

    def test_og_video_preferred_when_present(self):
        with mock.patch.object(tool, "http_get",
                               return_value=og_video_html().encode()):
            outcome, post = tool._fetch_og_meta(FAKE_CODE, "post")
        self.assertEqual(outcome, "ok")
        self.assertEqual(post["media_items"][0]["type"], "video")
        self.assertEqual(post["media_items"][0]["url"], CDN_MP4)
        self.assertEqual(post["media_items"][0]["poster_url"], CDN_JPEG)

    def test_ellipsis_caption_nulled(self):
        html = ('<meta property="og:title" content="u on Instagram: &quot;…&quot;">'
                f'<meta property="og:image" content="{CDN_JPEG}">')
        with mock.patch.object(tool, "http_get", return_value=html.encode()):
            _, post = tool._fetch_og_meta(FAKE_CODE, "post")
        self.assertIsNone(post["caption"])


class FollowerParsingTests(unittest.TestCase):
    def test_k_m_b(self):
        self.assertEqual(tool._parse_followers("12.3K followers"), 12300)
        self.assertEqual(tool._parse_followers("1.5M"), 1_500_000)
        self.assertEqual(tool._parse_followers("2B"), 2_000_000_000)
        self.assertEqual(tool._parse_followers("44"), 44)
        self.assertIsNone(tool._parse_followers("lots"))
        self.assertIsNone(tool._parse_followers(""))


class DecodeOrchestratorTests(unittest.TestCase):
    def test_slots_recorded_in_trace(self):
        calls = []

        def fake_json(code, kind):
            calls.append("embed_json")
            return "failed", None

        def fake_html(code, kind):
            calls.append("embed_html")
            return "ok", {"media_items": [{"type": "image", "url": CDN_JPEG}],
                          "extraction_source": "embed_html", "shortcode": code,
                          "media_id": FAKE_ID, "author": {}, "kind": None}

        with mock.patch.object(tool, "DECODE_SLOT_FNS", [
                ("embed_json", fake_json), ("embed_html", fake_html)]), \
             mock.patch.object(tool.time, "sleep"):
            post, trace = tool.decode_post(FAKE_CODE, "post")
        self.assertEqual(calls, ["embed_json", "embed_html"])
        self.assertEqual([t["outcome"] for t in trace], ["failed", "ok"])
        self.assertEqual(post["extraction_source"], "embed_html")

    def test_all_slots_fail_sets_error(self):
        with mock.patch.object(tool, "DECODE_SLOT_FNS", [
                ("a", lambda c, k: ("failed", None))]), \
             mock.patch.object(tool.time, "sleep"):
            tool.ERRORS.clear()
            post, trace = tool.decode_post(FAKE_CODE, "post")
            self.assertIsNone(post)
            self.assertEqual(tool.ERRORS[-1]["code"], tool.E_DECODE_FAILED)

    def test_slot_crash_does_not_kill_run(self):
        def boom(code, kind):
            raise RuntimeError("synthetic crash")

        def ok_slot(code, kind):
            return "ok", {"media_items": [{"type": "image", "url": CDN_JPEG}],
                          "extraction_source": "x", "author": {}}

        with mock.patch.object(tool, "DECODE_SLOT_FNS", [
                ("boom", boom), ("ok_slot", ok_slot)]), \
             mock.patch.object(tool.time, "sleep"):
            post, trace = tool.decode_post(FAKE_CODE, "post")
        self.assertIsNotNone(post)
        self.assertIn("crashed", trace[0]["outcome"])


if __name__ == "__main__":
    unittest.main()
