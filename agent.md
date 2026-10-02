# igagent — Operating Manual for AI Agents

**Read this file and nothing else.** Everything a machine needs to run
igagent end-to-end is here: preconditions, invocations, the full output
contract, a decision tree for exit codes, and known limitations.

---

## 1. What igagent is

igagent harvests **one public Instagram post** (post, carousel, reel, or
IGTV) per invocation and returns:

* every photo and video the public embed surface exposes, downloaded to
  disk and **verified by magic bytes**;
* `post_manifest.json` — a schema-versioned JSON envelope describing the
  post, its author, every media URL, every local file, every error, and
  the provenance of the decode slot that produced the result.

There is **no LLM at runtime**. igagent is a deterministic state machine
designed to be *called by* AI agents, not to be one.

## 2. Preconditions

* Python 3.9+ (stdlib only — no pip installs, no ffmpeg, no browser).
* Outbound HTTPS. That is all.
* No login, no cookies, no API keys, no env vars. There is nothing to
  configure; constants live at the top of `igagent.py` on purpose.

## 3. Invocation (three modes)

```bash
# 1. Full harvest — decode + verified downloads (default out: ./ig_media)
python igagent.py "https://www.instagram.com/p/<CODE>/"

# 2. Metadata only — no media files on disk
python igagent.py "<CODE>" --no-download

# 3. Machine contract — exactly one JSON object on stdout
python igagent.py "<input>" --json --quiet
```

Accepted inputs: `instagram.com/p|reel|reels|tv/<code>[/…]` (any of
www/m/l/ddinstagram/instagr.am, scheme-less, with query junk), share
links (`instagram.com/share/…`, expanded exactly one hop), and bare
shortcodes (5–32 chars of the URL-safe base64 alphabet that decode to a
positive media id).

Flags: `--out DIR` · `--no-download` · `--json` · `--quiet` · `--version`.

## 4. The output contract

`--json` stdout (summary) and `post_manifest.json` (full envelope) share
one schema: `schema/post-result.schema.json` (draft-07, `schema_version
"1.0"`). The envelope always carries every top-level key:

| key | meaning |
|---|---|
| `schema_version` | const `"1.0"` — bump = breaking contract change |
| `source` | `{tool, version, generated_at}` |
| `request` | `{input, shortcode, canonical_url, options{download_media}}` |
| `status` | `ok` \| `partial` \| `empty` |
| `post` | the post object, or `null` when empty |
| `errors` | structured `{stage, code, message, subject}` list |
| `metadata` | `duration_sec`, `decode_slots_tried` (provenance), `counts` |

`post.author`, `post.caption`, `post.created_at`, `post.like_count` are
**explicitly nullable** — a slot that does not expose a field yields
`null`, never a guess. `post.extraction_source` ∈ `embed_json` /
`embed_html` / `og_meta` — always recorded. `post.carousel.known` is
`true` only when carousel membership came from the payload itself.

Per-media entries carry `url`, `file` (local name or null),
`downloaded` (bool), `downloadable` (bool), and `reason` — e.g.
`no_video_url_exposed`, `url_outside_delivery_allowlist`,
`download_failed`.

## 5. Decision tree

```
exit 0
  ├─ status "ok"      → everything materialized; errors[] empty
  └─ status "partial" → post decoded AND downloaded>0 … treat media with
                        downloaded=false + reason as absent; read errors[]
exit 1
  ├─ status "empty"   → honest negative: post unavailable or undecodable.
  │                     errors[] says which. Do NOT retry blindly — 404 is
  │                     a filter, not always a verdict, but igagent already
  │                     walked every slot.
  └─ other            → infra-level failure; read errors[].code
exit 2
  └─ invalid_input    → your input, not the network. Fix the URL/code.
        codes: E_INVALID_INPUT, E_SHARE_EXPAND_FAILED
```

Decoder error codes: `E_POST_UNAVAILABLE` (all slots agree the post is
gone/private), `E_DECODE_FAILED` (all slots failed without a verdict).
Fetcher: `E_DOWNLOAD_FAILED`. Orchestrator: `E_MANIFEST_WRITE_FAILED`.

## 6. Copy-paste tasks

```bash
# Caption + author only
python igagent.py "<url>" --no-download --json --quiet \
  | python -c "import json,sys; p=json.load(open(sys.argv[1]))['post']; \
print(p['author']['username'], '|', p['caption'])" post_manifest.json 2>/dev/null

# Save a reel's video next to your notes
python igagent.py "https://www.instagram.com/reel/<CODE>/" --out ./notes_media

# Pipe-safe batch (one at a time — politeness is a hard constraint)
while read -r u; do python igagent.py "$u" --json --quiet >> results.ndjson; done < urls.txt
```

## 7. Known limitations (honest, not fixable by retry)

* **Carousel membership is tier-dependent.** The `embed_html` slot (most
  common from datacenter IPs) exposes only the first media item;
  `carousel.known` will be `false`. Full sidecars come from the
  `embed_json` slot when Instagram still serves it.
* **Reel video URLs are frequently not in the embed surface.** The video
  entry then reads `downloadable: false, reason: "no_video_url_exposed"`
  — that is the truth, not a bug.
* **Datacenter IPs hit walls.** Instagram's structured APIs (graphql,
  `/api/v1/media/<id>/info`) are walled from datacenter ranges and are
  deliberately *not* primary slots here. `og_meta` often requires a
  residential IP. See `docs/endpoint-matrix.md`.
* **One post per invocation.** Batch = loop with the tool's own politeness
  sleeps doing their work.

## 8. Hard constraints (do not ask the tool to break these)

1. No login/cookies/OAuth/browser — public content only, fails closed.
2. No GUI, no prompts.
3. No LLM at runtime.
4. stdlib only, single file, Python 3.9+.
5. Logs → stderr; data → stdout. Under `--json`, stdout is exactly one
   JSON object.
6. Files stay under `--out`. Media URLs must be https + `*.cdninstagram.com`
   / `*.fbcdn.net` or they are refused. IDs are validated before they
   touch the filesystem. Downloads are atomic (`.part` → `os.replace`)
   and magic-byte verified.
