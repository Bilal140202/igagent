# igagent

**An agentic Instagram content & media harvester for AI agents — no login, no API keys, no browser. MCP wrapper included.**

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Tests](https://img.shields.io/badge/tests-69%20offline-brightgreen) ![License](https://img.shields.io/badge/license-MIT-green) ![LLM](https://img.shields.io/badge/LLM%20at%20runtime-none-critical)

`igagent` is the Instagram sibling of [`xthread-agent`](https://github.com/Bilal140202/xthread-agent) (X/Twitter threads) and [`ytagent`](https://github.com/Bilal140202/ytagent) (YouTube). Same doctrine: a deterministic, slot-based, stdlib-only state machine that a cloud agent can call with one URL and read back one JSON contract.

```bash
python igagent.py "https://www.instagram.com/p/<CODE>/"
# → verified media on disk + post_manifest.json
```

---

## Why this exists

Cloud-based AI agents (GitHub Actions runners, sandboxed VMs, MCP hosts) cannot log into Instagram, and Instagram keeps proving that a login is not even the interesting boundary — the interesting boundary is *which door a machine is allowed through with no session at all*. Public embed pages are exactly such a door: Instagram serves them to any referrer, and for link unfurlers it renders the actual media straight into the HTML. igagent is built entirely on that observation.

What it gives you:

1. **One input, one artifact.** A post URL (or share link, or bare shortcode) in; a verified media directory plus `post_manifest.json` out.
2. **Honest negatives.** A deleted post is not an exception — it is `status: "empty"` with structured errors and a slot-by-slot provenance trace.
3. **Slots, not brands.** The three decode surfaces are interchangeable implementations of one contract. When Instagram kills one, you replace the slot — the pipeline never restructures.
4. **Verified delivery.** Files exist only after passing the CDN allowlist, a `Content-Length` check, and a magic-byte identity check. A tool that reports a file is vouching for its bytes.
5. **Truth layers over heuristics.** Carousel membership comes only from the payload (`edge_sidecar_to_children`) and is flagged `carousel.known` — never inferred from page layout. The shortcode itself decodes to the numeric media id by pure math, cross-checked against Instagram's `ig_cache_key`.
6. **Politeness as a hard constraint.** Bounded retries, 0.6 s decode sleeps, response caps, one post per invocation. The public surfaces this tool depends on are free; restraint is the rent.

## Architecture

```
            ┌──────────────────────────────────────────────────────┐
            │                    DISCOVERY                        │
            │  normalize p/reel/reels/tv URLs · instagr.am &      │
            │  ddinstagram mirrors · share links (1 hop) · bare   │
            │  shortcodes · shortcode ↔ media-id base64 math      │
            └───────────────────────────┬──────────────────────────┘
                                        ▼
            ┌──────────────────────────────────────────────────────┐
            │                     DECODE  (slots)                 │
            │  1. embed_json  — legacy rich payload               │
            │     (caption, metrics, sidecar children, author)    │
            │  2. embed_html  — unfurler SSR page                 │
            │     (media img/video, author, followers, cache key) │
            │  3. og_meta     — OpenGraph tags                    │
            │     (title/caption, og:image, og:video:secure_url)  │
            │  provenance trace [{"slot","outcome"}] on every run │
            └───────────────────────────┬──────────────────────────┘
                                        ▼
            ┌──────────────────────────────────────────────────────┐
            │                     DELIVER                        │
            │  https + *.cdninstagram.com / *.fbcdn.net only      │
            │  stream → .part → Content-Length ✓ → magic bytes ✓  │
            │  → os.replace (atomic) → files + post_manifest.json │
            └──────────────────────────────────────────────────────┘
```

Each tier fails closed: a slot that finds nothing hands control to the next slot and the attempt is recorded; only "everything failed" becomes a run-level error.

## Quickstart

```bash
# full harvest (decode + verified downloads)
python igagent.py "https://www.instagram.com/p/<CODE>/" --out ./ig_media

# metadata only
python igagent.py "<CODE>" --no-download

# the machine contract: exactly one JSON object on stdout
python igagent.py "<input>" --json --quiet
```

### For AI agents

```bash
python igagent.py agent-instructions 2>/dev/null || true   # not needed —
# the operating manual IS agent.md: read that file and nothing else.
```

The three-command contract:

| command | returns | exit |
|---|---|---|
| `igagent.py "<input>" --json --quiet` | summary JSON on stdout, full envelope at `manifest_path` | 0 ok/partial · 1 empty · 2 invalid |
| `igagent.py "<input>" --no-download --json --quiet` | same, no files on disk | same |
| `igagent.py --version` | `igagent 1.0.0` | 0 |

## CLI reference

```
igagent.py <input> [--out DIR] [--no-download] [--json] [--quiet] [--version]

<input>         instagram.com /p|reel|reels|tv/<code>/ · mirror hosts ·
                share links (instagram.com/share/…) · bare shortcodes
--out DIR       output directory (default: ig_media)
--no-download   decode only; manifest still written
--json          one JSON summary object on stdout (stderr silenced)
--quiet         silence human logs on stderr
```

Accepted input shapes: `https://www.instagram.com/p/<CODE>/`,
`instagram.com/reel/<CODE>?utm_source=…`, `m./l./ddinstagram/instagr.am`
mirrors, `https://www.instagram.com/share/<token>/`, and bare shortcodes
(5–32 chars of `A-Za-z0-9_-` that decode to a positive media id).

### JSON output (for AI agents)

```json
{
  "ok": true,
  "status": "ok",
  "shortcode": "<CODE>",
  "media_id": "1949525278281554174",
  "canonical_url": "https://www.instagram.com/p/<CODE>/",
  "post_type": "image",
  "extraction_source": "embed_html",
  "images": 1, "videos": 0,
  "downloaded": 1, "failed_downloads": 0,
  "out_dir": "ig_media",
  "manifest_path": "ig_media/post_manifest.json",
  "errors": [],
  "duration_sec": 2.2
}
```

The full envelope (`post_manifest.json`) adds the post object: caption,
`created_at`, author (`username`, `followers`, `verified`, … — explicit
nulls when a slot does not expose them), `media.images[]` /
`media.videos[]` with `url / file / downloaded / downloadable / reason`,
`carousel{known, child_count}`, `errors[]` with stable codes, and
`metadata.decode_slots_tried` — the provenance trace. The draft-07 schema
is bundled at `schema/post-result.schema.json`.

## For MCP hosts

`python mcp_server.py` speaks newline-delimited JSON-RPC 2.0 on stdio —
stdlib only, no `mcp` package. Register it in Claude Desktop / Zed:

| tool | what it does |
|---|---|
| `extract_post` | full harvest → verified files + envelope |
| `lookup_post` | metadata-only decode (no downloads) |
| `read_manifest` | return an existing `post_manifest.json` (refuses anything else) |
| `get_schema` | the draft-07 envelope schema |

Error policy: an honest empty result is **not** an MCP error; a bad tool
argument, timeout, or crash is.

## Documentation

| file | role |
|---|---|
| [`agent.md`](agent.md) | the operating manual for AI agents — read this file and nothing else |
| [`agents.md`](agents.md) | perfection-based role prompts for the five pipeline roles |
| [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) | maintainer manifesto: why, load-bearing walls, fragile parts, debts |
| [`docs/endpoint-matrix.md`](docs/endpoint-matrix.md) | living endpoint status table + maintenance protocol |
| [`schema/post-result.schema.json`](schema/post-result.schema.json) | the output contract, machine-checkable |
| [`RELEASE_NOTES.md`](RELEASE_NOTES.md) | version history |

## Constraints (non-negotiable)

1. **No login, no cookies, no OAuth, no browser.** Public content only; everything fails closed.
2. **No GUI, no interactive prompts.** 100% non-interactive CLI.
3. **No LLM at runtime.** Deterministic state machine — the "agent" is designed *for* AI agents, not made of one.
4. **stdlib only.** Single file, zero pip dependencies, Python 3.9+.
5. **Logs on stderr, data on stdout.** Always pipe-safe.
6. **Files stay under the output directory.** CDN allowlist, ID validation, atomic writes, magic-byte verification.

## Requirements

Python 3.9+ and outbound HTTPS. Nothing else — no pip, no ffmpeg, no
browser, no env vars, no config files.

## Installation

```bash
# as a tool (after PyPI publish)
pip install igagent
igagent "<url>" --json

# from source
git clone https://github.com/Bilal140202/igagent.git
python igagent/igagent.py "<url>"
# or
python -m igagent "<url>"
```

## Testing

```bash
python -m unittest discover -s tests -p "test_*.py"
# 69 tests, ~1s, zero network — synthetic fixtures only, never real IDs
```

## Verified behavior (as shipped)

| claim | evidence |
|---|---|
| `embed_html` slot harvests a live public image post from a datacenter IP | live run: `status=ok`, 1 image downloaded (33 KB, JPEG magic), `media_id` from `ig_cache_key` |
| shortcode ↔ media-id math is exact | round-trip property tests (50 random ids) |
| dead posts produce honest empties | live run: `status=empty`, `E_DECODE_FAILED`, exit 1 |
| magic-byte gate rejects HTML masquerading as media | offline tests |
| lookalike CDN hosts (`evil-cdninstagram.com`, `cdninstagram.com.evil.io`) refused | offline tests |
| MCP handshake + 4-tool registry | offline stdio probe |

Re-verify against your own vantage point and update
`docs/endpoint-matrix.md` — that is the protocol.

## Limitations (the honest section)

* **Reel/video URLs are frequently not exposed** by the embed surface. The
  video entry then reports `downloadable: false, reason:
  "no_video_url_exposed"` — this is the truth, not a bug. Stories,
  live, and private accounts are out of scope entirely.
* **Carousel depth is slot-dependent.** The commonly-served unfurler view
  shows only the primary item; `carousel.known=false` says so honestly.
  Full sidecars require the legacy `embed_json` payload.
* **Datacenter IPs get walls.** Instagram's structured APIs (graphql,
  media info) are walled from cloud ranges and deliberately not slots;
  `og_meta` often needs a residential IP.
* **Instagram changes surfaces without notice.** The slot architecture
  and the endpoint matrix exist precisely because everything upstream of
  this tool is borrowed ground.

## Legal / ethics

igagent accesses only publicly served documents over unauthenticated
HTTP(S), with politeness sleeps and hard caps, and it never circumvents
a paywall, a login, or a private post. Respect creators: media and
captions remain the property of their authors; downstream use is your
responsibility. Do not use this tool at volumes that constitute abuse.

## FAQ

**Why is there no login option?** Because the calling agent is a cloud
VM by definition — no session, no cookies. The whole design is "what
can a sessionless machine legitimately get?" — and the answer is
documented, versioned, and fail-closed.

**Why is `status` often `partial` instead of `ok`?** `partial` means the
post was decoded but something failed (e.g. a video URL was never
exposed so nothing could be downloaded). The media entries carry the
per-item `reason`. `errors[]` is the full story.

**A decode stopped working — is igagent broken?** Check
`docs/endpoint-matrix.md` first. Surfaces flip; the matrix is the
impersonal record of flips, and slots are how they get absorbed.

**Does it work for stories or private accounts?** No, by design — both
require authentication, which violates constraint 1.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

* [`xthread-agent`](https://github.com/Bilal140202/xthread-agent) — the architecture, the docs-as-contract system, the MCP wrapper, and the phrase "restraint is the rent".
* [`ytagent`](https://github.com/Bilal140202/ytagent) — "never trust a method's self-report", the verification doctrine this project merged into its delivery tier.
* The mirror/unfurler ecosystem — the doors that were already open.

## Links

* Repository: <https://github.com/Bilal140202/igagent>
* Issues: <https://github.com/Bilal140202/igagent/issues>
* Siblings: [`xthread-agent`](https://github.com/Bilal140202/xthread-agent) · [`ytagent`](https://github.com/Bilal140202/ytagent)
