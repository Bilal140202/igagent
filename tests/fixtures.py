"""100% synthetic fixtures — no real IDs, no real accounts, no network.

Repo rule (inherited from the sibling projects): tests never contain real
usernames, real shortcodes of live posts, or real CDN URLs.  Everything
here is fabricated to mirror the *shape* of the public surfaces as
documented in docs/endpoint-matrix.md.
"""

FAKE_CODE = "SYNcodeTEST01"            # alphabet-only, decodes to a big int
FAKE_ID = "86788987894072359861557"    # shortcode_to_id(FAKE_CODE), precomputed
FAKE_CACHE_KEY = "ODY3ODg5ODc4OTQwNzIzNTk4NjE1NTc%3D"  # b64(FAKE_ID), URL-encoded

CDN_HOST = "scontent-fake.cdninstagram.com"
CDN_JPEG = (f"https://{CDN_HOST}/v/t51.2885-15/synthetic-photo.jpg"
            f"?_nc_cat=104&ig_cache_key={FAKE_CACHE_KEY}")
CDN_MP4 = f"https://{CDN_HOST}/v/t66.30100-16/synthetic-video.mp4"
CDN_PNG = f"https://{CDN_HOST}/v/t51.2885-15/synthetic-icon.png"
CDN_WEBP = f"https://{CDN_HOST}/v/t51.2885-19/synthetic-avatar.webp"
OUTSIDE_URL = "https://evil.example.com/media.mp4"
HTTP_URL = "http://scontent-fake.cdninstagram.com/a.jpg"

JPEG_HEAD = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 16
PNG_HEAD = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
MP4_HEAD = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 16
HTML_HEAD = b"<!DOCTYPE html><html><body>not media</body></html>"

# ── Rich embed payload (embed_json slot, Shape A/B) ─────────────────────────
RICH_SM = {
    "shortcode": FAKE_CODE,
    "id": FAKE_ID,
    "__typename": "GraphSidecar",
    "taken_at_timestamp": 1699999999,
    "edge_media_to_caption": {"edges": [{"node": {"text": "synthetic caption"}}]},
    "edge_media_to_comment": {"count": 12},
    "edge_media_preview_like": {"count": 3456},
    "dimensions": {"width": 1080, "height": 1080},
    "display_url": CDN_JPEG,
    "owner": {"id": "9998887776665554443", "username": "synthetic_user",
              "full_name": "Synthetic User", "is_verified": True,
              "profile_pic_url": CDN_WEBP},
    "edge_sidecar_to_children": {"edges": [
        {"node": {"__typename": "GraphImage", "display_url": CDN_JPEG,
                  "dimensions": {"width": 1080, "height": 1080},
                  "accessibility_caption": "synthetic alt one"}},
        {"node": {"__typename": "GraphVideo", "is_video": True,
                  "video_url": CDN_MP4, "display_url": CDN_JPEG,
                  "video_duration": 21.5,
                  "dimensions": {"width": 1080, "height": 1080}}},
        {"node": {"__typename": "GraphImage", "display_url": CDN_JPEG,
                  "dimensions": {"width": 1080, "height": 1080}}},
    ]},
}


def rich_embed_html() -> str:
    """Shape A: window.__additionalDataLoaded('extra', {...});"""
    import json
    return (
        "<!DOCTYPE html><html><head><title>Instagram</title></head><body>"
        "<script>window.__additionalDataLoaded('extra',"
        + json.dumps({"shortcode_media": RICH_SM}) + ");</script>"
        "</body></html>"
    )


# ── SSR embed HTML (embed_html slot) ────────────────────────────────────────
def ssr_embed_html() -> str:
    """The unfurler-rendered embed page shape (image post)."""
    return f"""<!DOCTYPE html><html lang="en"><head><title>Instagram</title></head>
<body class="">
<div class="Header">
  <div class="HeaderProfile">
    <img class="Avatar" src="{CDN_WEBP}" alt="">
    <div class="HeaderInfo">
      <span class="UsernameText">synthetic_user</span>
      <div class="HeaderSecondaryContent">
        <span class="FollowerCountText">12.3K followers</span>
      </div>
    </div>
  </div>
  <div class="HeaderCta">
    <a class="ViewProfileButton" href="https://www.instagram.com/synthetic_user/?utm_source=ig_embed"
       data-log-event="profileButtonClick" target="_blank">View profile</a>
  </div>
</div>
<div class="Content EmbedFrame">
  <a class="EmbeddedMedia" href="https://www.instagram.com/p/{FAKE_CODE}/?utm_source=ig_embed"
     data-log-event="mediaClick" target="_blank">
    <img class="EmbeddedMediaImage" alt="Instagram post shared by &#064;synthetic_user"
         src="{CDN_JPEG}">
  </a>
</div>
</body></html>"""


def ssr_unavailable_html() -> str:
    return ("<!DOCTYPE html><html><head><title>Instagram</title></head>"
            "<body><p>Sorry, this page isn't available.</p></body></html>")


# ── og_meta page ────────────────────────────────────────────────────────────
def og_meta_html() -> str:
    return f"""<!DOCTYPE html><html><head>
<meta property="og:site_name" content="Instagram">
<meta property="og:url" content="https://www.instagram.com/p/{FAKE_CODE}/">
<meta property="og:type" content="article">
<meta property="og:title" content="synthetic_user on Instagram: &quot;synthetic og caption here&quot;">
<meta property="og:description" content="123 likes, 4 comments - synthetic_user on January 1, 2024">
<meta property="og:image" content="{CDN_JPEG}">
</head><body></body></html>"""


def og_video_html() -> str:
    return f"""<!DOCTYPE html><html><head>
<meta property="og:title" content="synthetic_user on Instagram: &quot;…&quot;">
<meta property="og:video:secure_url" content="{CDN_MP4}">
<meta property="og:image" content="{CDN_JPEG}">
</head><body></body></html>"""
