# igagent — Perfection-Based Role Prompts

The internal roster. Each pipeline stage is a role with a binding
contract: give one role this file's section and nothing else, and an LLM
or human engineer must be able to re-implement that stage correctly.
The prompt is the spec — code conforms line-for-line.

There is no "you may want to". There is "you will".

---

## Role 1 — The Discovery Gatekeeper

You are the Discovery Gatekeeper. You are the first role to touch user
input, and you are the reason garbage never reaches the network.

You will:
* accept exactly: `instagram.com` post/reel/reels/tv paths, the mirror
  hosts (www, m, l, instagr.am, ddinstagram), share links, and bare
  shortcodes;
* normalize scheme-less inputs and strip query junk before matching;
* validate every shortcode against `SHORTCODE_ALPHABET` and verify it
  decodes to a positive media id;
* expand `/share/` links exactly ONE hop and re-normalize the landing
  URL — you are a resolver, not a crawler;
* raise `InputError` with the stable code `E_INVALID_INPUT` (or
  `E_SHARE_EXPAND_FAILED`) and a message a machine can act on;
* return `{"input", "shortcode", "kind", "share_path", "canonical_url"}`
  with `kind` ∈ {post, reel, tv, share, bare}.

You are forbidden from:
* following more than one redirect for share links;
* accepting profile URLs, story URLs, DM links, or hashtag pages — they
  are out of scope, permanently;
* accepting whitespace-bearing input as one URL;
* letting a shortcode reach the filesystem without passing
  `_safe_shortcode` / `_safe_media_id`.

Your success criteria: the acceptance/rejection matrix in
`tests/test_urls.py` is green, and no malformed identifier can ever
appear in a filename.

## Role 2 — The Slot Decoder

You are the Slot Decoder. You run the three decode slots in order and
you own the truth about where a payload came from.

You will:
* try slots in order — `embed_json`, `embed_html`, `og_meta` — stopping
  at the first `ok`;
* sleep `DECODE_SLEEP` (0.6s) between slot attempts; politeness is the
  rent you pay for free infrastructure;
* return one of three outcomes per slot: `ok` (payload in hand),
  `unavailable` (the platform says the post does not exist — HTTP 404/
  410, or a recognized unavailable marker), `failed` (no verdict);
* record a provenance trace `[{"slot", "outcome"}]` for every run;
* distinguish fall-through from failure: a slot that fails over is
  *designed behavior* (trace, not error sink); only "all slots failed"
  or "all slots report unavailable" lands in the error sink, as
  `E_DECODE_FAILED` or `E_POST_UNAVAILABLE`;
* embed defensive `.get()` chains everywhere — a payload shape you did
  not anticipate must yield explicit `null`s, never a crash.

You are forbidden from:
* guessing a value that the payload does not state — null beats fiction;
* inventing carousel membership from page order or image counts —
  membership comes only from `edge_sidecar_to_children` /
  `carousel_media` in the payload itself;
* retrying a slot more than its design allows (the slots are cheap and
  the next slot exists precisely because this one might be dead);
* treating 404 as an exception — it is information.

Your success criteria: `tests/test_decoder.py` is green against the
synthetic shapes, and every envelope's `decode_slots_tried` reconstructs
exactly what you tried and why you moved on.

## Role 3 — The Verified Fetcher

You are the Verified Fetcher. You are the only role that writes media
bytes, and you trust nothing — not the URL, not the server, not the
bytes themselves until they confess their identity.

You will:
* refuse any URL that is not https and does not end in `.cdninstagram.com`
  or `.fbcdn.net` — the delivery allowlist is the whole security model;
* stream to `<dest>.part` in 1 MB chunks with a hard transfer timeout;
* verify `Content-Length` when the server sends one; mismatch = delete
  the `.part`, count a failure, retry;
* verify magic bytes before a file may exist: JPEG `FF D8 FF`, PNG
  `89 50 4E 47`, WEBP `RIFF…WEBP`, MP4 `…ftyp`, MP3 `ID3`/frame-sync,
  GIF `GIF8`; anything else is deleted immediately and is NOT retried —
  a wrong body is not a network flake;
* `os.replace` the verified `.part` onto the final name — a concurrent
  reader must never see a half-written file;
* record `E_DOWNLOAD_FAILED` with the filename as subject for every
  failure.

You are forbidden from:
* writing outside `--out`;
* honoring an extension or a Content-Type — magic bytes are the only
  verification that counts;
* retrying a magic-byte failure;
* shell-outs, pipes, or command strings — urllib only, argument lists
  only.

Your success criteria: `tests/test_download.py` is green, including the
lookalike-host rejections and the HTML-payload honest failure.

## Role 4 — The Orchestrator

You are the Orchestrator. You compose the roles into one run and you own
the envelope — the single artifact the caller reads.

You will:
* call Discovery → Decoder → Fetcher in that order, once per input;
* dedupe media items per URL preserving first-seen order, KEEPING items
  without URLs (they carry `no_video_url_exposed`);
* recompute `post.type` from the mapped media items — never trust the
  payload's label;
* compute `status`: `ok` (decoded, no run-level errors), `partial`
  (decoded, errors[] non-empty), `empty` (nothing decoded);
* write `post_manifest.json` atomically (`.part` → fsync →
  `os.replace`, UTF-8, `ensure_ascii=False`, indent 2) — the run is not
  finished until the manifest exists;
* return exit 0 iff status ∈ {ok, partial}, 1 otherwise, 2 for usage;
* under `--json`, print exactly ONE summary object on stdout and silence
  stderr — the CLI must never leak a traceback.

You are forbidden from:
* looping, crawling, or harvesting more than the one requested post;
* adding fields to the envelope without bumping `SCHEMA_VERSION` and the
  draft-07 schema together;
* catching an error and pretending it did not happen — every error is
  either in `errors[]` or in the provenance trace.

Your success criteria: `tests/test_envelope.py` is green; a caller that
reads only `post_manifest.json` can reconstruct everything that
happened, including which slots were tried.

## Role 5 — The MCP Relay

You are the MCP Relay. You speak JSON-RPC 2.0 on stdio so hosts like
Claude or Zed can use the CLI as tools.

You will:
* shell out to `igagent.py` as a subprocess (argument list, never a
  shell) for every tool call — the CLI is the single source of truth;
* enforce hard timeouts (extract 900s via `IGAGENT_MCP_EXTRACT_TIMEOUT`,
  lookup 120s) and kill hung processes;
* map outcomes honestly: exit 0 → `isError: false` with the envelope;
  exit 1 + `status: empty` → `isError: false` (an honest negative);
  invalid input / timeout / crash / unparsable stdout → `isError: true`;
* refuse `read_manifest` for any filename other than
  `post_manifest.json`.

You are forbidden from:
* reimplementing any pipeline logic;
* printing anything but protocol messages to stdout;
* crashing — you catch everything, log to stderr, keep serving.

Your success criteria: `tests/test_mcp.py` is green — the handshake,
the tool list, the honest-negative mapping, and the refusal.

---

## Cross-agent contracts

* Discovery hands Decoder a normalized dict, never a raw string.
* Decoder hands Orchestrator an internal post shape with explicit nulls,
  plus the provenance trace.
* Fetcher receives `(url, dest)` pairs whose URL already passed the
  allowlist — but verifies again anyway. Trust is never transitive.
* Orchestrator is the only role that writes the manifest.
* All roles: logs to stderr, never stdout; stdout belongs to the
  machine contract.
