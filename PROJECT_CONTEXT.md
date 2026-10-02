# PROJECT_CONTEXT.md — Read Me Before Touching Anything

This is the maintainer manifesto, in the tradition of the sibling
projects. It explains why the code is the way it is, which walls are
load-bearing, which parts are fragile, and what is deliberately left
undone. Code explains *how*; this explains *why*.

## 1. Why this exists

The sibling pair proved the same thesis on two platforms: a
sessionless machine can still get real work done if you build on the
public surfaces that platforms serve for their own reasons — embeds for
link unfurling, CDNs for delivery, mirrors for resilience. Instagram is
the hardest of the three platforms because its structured APIs are the
most aggressively walled, and that is exactly why it is the best
demonstration of the doctrine: the doors that remain open are the
unfurler-rendered embed page and the CDN behind it.

## 2. Load-bearing walls (do not casually reverse)

* **Single file, stdlib only.** `igagent.py` is the product; the package
  directory is a byte-identical synced copy (drift fails CI). The
  deployment story — copy one file into a bare sandbox — is a feature.
* **Slots, not brands.** `embed_json` / `embed_html` / `og_meta` are
  interchangeable implementations of one contract. When one dies,
  replace the slot function in `DECODE_SLOT_FNS`; do not restructure.
* **Fall-through is not failure.** A slot that yields `failed` hands
  control to the next slot and shows up in the provenance trace — not
  in `errors[]`. Run-level errors are reserved for verdicts ("all slots
  failed") and fetcher/orchestrator failures. This distinction is what
  keeps `status` meaningful.
* **The delivery allowlist is the security model.** `*.cdninstagram.com`
  and `*.fbcdn.net`, https only. Everything else is refused before a
  socket opens. Together with magic-byte verification and atomic
  writes, this is the whole trust story.
* **Explicit nulls.** A field the slot did not expose is `null`, never
  a guess, never an empty string, never a fabricated default. This is
  the difference between a tool and a confabulator.

## 3. Fragile parts (ranked by fragility)

1. **The unfurler UA pivot.** The whole embed_html slot depends on
   Instagram serving the SSR page to `facebookexternalhit`. If they
   drop that, slot 2 dies overnight — the trace will say so.
2. **Class-name scraping.** `EmbeddedMediaImage`, `ViewProfileButton`,
   `FollowerCountText` are CSS class names, rot-fast by nature. The
   parsers are regexes on purpose: cheap, replaceable, honest about
   their venue.
3. **The `ig_cache_key` id signal.** Base64-encoded media id riding on
   media URLs. If Instagram drops the parameter, the fallback is the
   shortcode math (pure, local, also exact).
4. **The `contextJSON` / `__additionalDataLoaded` shapes.** Legacy
   payload shapes; each may vanish. Each is one regex and one
   balanced-JSON extraction.

## 4. Deliberate debts (known, documented, not fixed)

* The `embed_html` slot exposes only the primary media for carousels —
  full sidecars depend on the legacy payload surviving. `carousel.known`
  exists so callers never have to wonder.
* Video URLs from the embed surface are commonly absent; the
  `no_video_url_exposed` reason is the honest record of that ceiling.
  A future slot (e.g. a public mirror worker) is the fix — not UA
  tricks against the walled APIs.
* `demo.py`, `mcp_server.py`, and the tests all re-derive the tool path
  relative to their own file. If you move files, move them together.
* The endpoint matrix is verified from one vantage point (a datacenter
  VM). The protocol asks every maintainer to re-verify from theirs.

## 5. Design principles (do not casually reverse)

* **Honesty over completeness.** `status: partial`, structured
  `errors[]`, `reason:` strings — never fabricate a value.
* **404 is a filter, not an error.** But when every slot reports
  unavailable, the honest verdict is `E_POST_UNAVAILABLE` — a verdict,
  recorded once, at the run level.
* **Politeness is a hard constraint.** 0.6 s decode sleeps, bounded
  retries, response caps, one post per invocation. "Restraint is the
  rent."
* **The docs are the spec.** `agent.md` (for machines) and `agents.md`
  (role prompts) are binding. Code conforms to them; when it cannot,
  the docs change first, deliberately.
* **Synthetic fixtures only.** No real usernames, codes, or CDN URLs in
  the repo — not in tests, not in docs, not in issues.

## 6. How to change something safely

1. Say which wall you are touching, out loud, in the PR description.
2. New behavior → tests first (offline, synthetic, fast).
3. New envelope field → bump `SCHEMA_VERSION`, update the draft-07
   schema, update `agent.md` §4, in one commit.
4. New/dead slot → update `DECODE_SLOT_FNS`, the trace test, and the
   endpoint matrix row.
5. Run: full suite → `sync_package.py --check` → CLI smoke → MCP probe.
