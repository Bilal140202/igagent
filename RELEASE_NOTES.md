# Release Notes

## v1.0.0 — 2026-10-02

Initial public release. Sibling to `xthread-agent` (X/Twitter threads)
and `ytagent` (YouTube) — same doctrine, new platform.

### The pipeline

| Tier | Slots | Notes |
|---|---|---|
| Discovery | normalize / share-expand | shortcode ↔ media-id round-trip math, one-hop share links |
| Decode | `embed_json` → `embed_html` → `og_meta` | provenance trace on every run; honest nulls |
| Deliver | CDN fetcher | `*.cdninstagram.com` / `*.fbcdn.net` allowlist, magic-byte verification, atomic writes |

### Highlights

* Single-file stdlib-only tool (`igagent.py`), Python 3.9+, zero pip
  dependencies, byte-identical PyPI package (`pip install igagent`).
* `post_manifest.json` envelope (schema_version 1.0) with draft-07
  schema; `--json` stdout contract; exit codes 0/1/2.
* Carousel membership taken only from the payload (truth layer),
  `carousel.known` records whether membership was payload-proven.
* MCP stdio server (`mcp_server.py`): `extract_post`, `lookup_post`,
  `read_manifest`, `get_schema`.
* 69 offline tests, ~1s, zero network; CI matrix 3.9–3.13.
* `demo.py` consumes the tool exactly as an external agent would.

### Known limits (documented, honest)

* Datacenter IPs: structured Instagram APIs are walled; the tool relies
  on embed/unfurler surfaces — reel video URLs are often not exposed
  (`reason: no_video_url_exposed`).
* Carousel children only via the `embed_json` slot when Instagram still
  serves the legacy rich payload.
