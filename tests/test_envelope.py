"""harvest() end-to-end with patched slots and downloads (fully offline)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import tool
from fixtures import (CDN_JPEG, CDN_MP4, FAKE_CODE, FAKE_ID, JPEG_HEAD,
                      MP4_HEAD)


def _fake_file_response(head):
    """A file-like urlopen result: returns `head` once, then EOF."""
    state = {"consumed": False}
    resp = mock.MagicMock()

    def _read(n):
        if state["consumed"]:
            return b""
        state["consumed"] = True
        return head

    resp.read = _read
    resp.headers = {}
    cm = mock.MagicMock()
    cm.__enter__ = mock.Mock(return_value=resp)
    cm.__exit__ = mock.Mock(return_value=False)
    return cm


class HarvestTests(unittest.TestCase):
    def setUp(self):
        tool.ERRORS.clear()

    def _run(self, items, download_ok=True):
        """Decode one synthetic post exposing `items`, all downloads ok."""
        post = {
            "media_id": FAKE_ID, "shortcode": FAKE_CODE, "kind": None,
            "type": None, "caption": "synthetic caption",
            "created_at": 1699999999, "like_count": 42,
            "comment_count": 7,
            "author": {"username": "synthetic_user", "full_name": None,
                       "avatar_url": None, "verified": None,
                       "user_id": None, "followers": None},
            "media_items": items, "extraction_source": "embed_html",
        }
        with mock.patch.object(tool, "DECODE_SLOT_FNS", [
                ("synthetic", lambda c, k: ("ok", post))]), \
             mock.patch.object(tool.time, "sleep"):
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "out"
                if download_ok:
                    # Every urlopen call is one file download: media items
                    # plus one poster per video that exposes poster_url.
                    heads = []
                    for i in items:
                        heads.append(MP4_HEAD if i["type"] == "video"
                                     else JPEG_HEAD)
                        if i["type"] == "video" and i.get("poster_url"):
                            heads.append(JPEG_HEAD)
                    with mock.patch.object(
                            tool.urllib.request, "urlopen",
                            side_effect=[_fake_file_response(h)
                                         for h in heads]):
                        env = tool.harvest(
                            {"input": FAKE_CODE, "shortcode": FAKE_CODE,
                             "kind": "post",
                             "canonical_url": f"https://www.instagram.com/p/{FAKE_CODE}/"},
                            out, do_download=True)
                else:
                    env = tool.harvest(
                        {"input": FAKE_CODE, "shortcode": FAKE_CODE,
                         "kind": "post",
                         "canonical_url": f"https://www.instagram.com/p/{FAKE_CODE}/"},
                        out, do_download=False)
                files = sorted(p.name for p in out.iterdir())
        return env, files

    def test_image_post_ok(self):
        env, files = self._run([{"type": "image", "url": CDN_JPEG,
                                 "poster_url": None, "width": 1080,
                                 "height": 1080, "alt": None,
                                 "duration": None, "child_index": None}])
        self.assertEqual(env["status"], "ok")
        self.assertEqual(env["schema_version"], "1.0")
        self.assertEqual(env["post"]["media_id"], FAKE_ID)
        self.assertEqual(env["post"]["type"], "image")
        self.assertEqual(env["post"]["author"]["username"], "synthetic_user")
        self.assertEqual(env["metadata"]["counts"]["downloaded_media"], 1)
        self.assertEqual(env["errors"], [])
        self.assertIn(f"{FAKE_CODE}_p1.jpg", files)
        self.assertIn("post_manifest.json", files)

    def test_carousel_known_membership(self):
        items = [
            {"type": "image", "url": CDN_JPEG, "child_index": 1,
             "poster_url": None, "width": None, "height": None,
             "alt": None, "duration": None},
            {"type": "video", "url": CDN_MP4, "child_index": 2,
             "poster_url": CDN_JPEG, "width": None, "height": None,
             "alt": None, "duration": 5.0},
        ]
        env, files = self._run(items)
        self.assertEqual(env["post"]["type"], "carousel")
        self.assertTrue(env["post"]["carousel"]["known"])
        self.assertEqual(env["post"]["carousel"]["child_count"], 2)
        self.assertEqual(env["metadata"]["counts"]["videos"], 1)
        self.assertIn(f"{FAKE_CODE}_p1.jpg", files)
        self.assertIn(f"{FAKE_CODE}_v1.mp4", files)
        self.assertIn(f"{FAKE_CODE}_v1_poster.jpg", files)

    def test_no_download_metadata_only(self):
        env, files = self._run([{"type": "image", "url": CDN_JPEG,
                                 "poster_url": None, "width": None,
                                 "height": None, "alt": None,
                                 "duration": None, "child_index": None}],
                               download_ok=False)
        self.assertEqual(env["status"], "ok")
        self.assertEqual(env["metadata"]["counts"]["downloaded_media"], 0)
        self.assertEqual(files, ["post_manifest.json"])
        self.assertFalse(env["post"]["media"]["images"][0]["downloaded"])
        self.assertTrue(env["post"]["media"]["images"][0]["downloadable"])

    def test_degraded_video_reason(self):
        env, files = self._run([{"type": "video", "url": None,
                                 "poster_url": CDN_JPEG, "width": None,
                                 "height": None, "alt": None,
                                 "duration": None, "child_index": None}],
                               download_ok=False)
        self.assertEqual(env["status"], "ok")
        vid = env["post"]["media"]["videos"][0]
        self.assertFalse(vid["downloadable"])
        self.assertEqual(vid["reason"], "no_video_url_exposed")

    def test_outside_allowlist_not_attempted(self):
        env, files = self._run([{"type": "image",
                                 "url": "https://evil.example.com/a.jpg",
                                 "poster_url": None, "width": None,
                                 "height": None, "alt": None,
                                 "duration": None, "child_index": None}])
        img = env["post"]["media"]["images"][0]
        self.assertFalse(img["downloadable"])
        self.assertEqual(img["reason"], "url_outside_delivery_allowlist")

    def test_manifest_json_shape(self):
        env, files = self._run([{"type": "image", "url": CDN_JPEG,
                                 "poster_url": None, "width": None,
                                 "height": None, "alt": None,
                                 "duration": None, "child_index": None}])
        # required top-level keys — explicit nullability is the law
        for key in ("schema_version", "source", "request", "status",
                    "post", "errors", "metadata"):
            self.assertIn(key, env)
        self.assertEqual(env["source"]["tool"], "igagent")
        self.assertEqual(env["request"]["options"], {"download_media": True})


class EmptyPathTests(unittest.TestCase):
    def test_all_slots_fail_envelope(self):
        tool.ERRORS.clear()
        with mock.patch.object(tool, "DECODE_SLOT_FNS", [
                ("a", lambda c, k: ("failed", None))]), \
             mock.patch.object(tool.time, "sleep"):
            with tempfile.TemporaryDirectory() as td:
                env = tool.harvest(
                    {"input": "x", "shortcode": "ZqwxkPlmN0q",
                     "kind": "post",
                     "canonical_url": "https://www.instagram.com/p/ZqwxkPlmN0q/"},
                    Path(td), do_download=False)
                self.assertEqual(env["status"], "empty")
                self.assertIsNone(env["post"])
                self.assertEqual(env["errors"][-1]["code"],
                                 tool.E_DECODE_FAILED)


if __name__ == "__main__":
    unittest.main()
