# Endpoint Matrix — igagent

The living trust anchor. Every public surface igagent depends on, with
its status and the date it was last verified **from a named vantage
point**. A row without a "last verified" date is folklore, not evidence.

Maintenance protocol (impersonal, four steps):

1. Re-verify the row by hand (one curl, one look at the body).
2. Update the row + the "last verified" line.
3. Open an issue if a surface flipped (up or down) — flips are facts,
   not failures.
4. Keep it impersonal: "as verified from <vantage>, <date>".

## Decode slots

| Surface | Role | Status | Failure signature | Last verified |
|---|---|---|---|---|
| `www.instagram.com/{p,reel,tv}/<code>/embed/captioned/` (browser UA) | slot 1 `embed_json` | Serves shell only for many IPs; legacy `__additionalDataLoaded` / `contextJSON` payloads rare | `failed` (no JSON found) | 2026-10-02, datacenter VM (shell-only response observed) |
| `www.instagram.com/{p,reel,tv}/<code>/embed/captioned/` (`facebookexternalhit` UA) | slot 2 `embed_html` | WORKING for public image posts: SSR media img, author link, follower count, `ig_cache_key` media id | "unavailable" markers on dead posts; empty shell on some video posts | 2026-10-02, datacenter VM (live harvest OK) |
| `www.instagram.com/{p,reel,tv}/<code>/` (`facebookexternalhit` UA) | slot 3 `og_meta` | Walled from datacenter IPs (no og:image served); expected to work from residential ranges | no og: tags → `failed` | 2026-10-02, datacenter VM (walled) |
| `i.instagram.com/api/v1/media/<id>/info/` | rejected as slot | 302 → login wall from datacenter IPs; app-id header does not save it | 302 / login HTML | 2026-10-02, datacenter VM |
| `www.instagram.com/graphql/query` (xdt_shortcode_media doc_id) | rejected as slot | 403 from datacenter IPs | 403 HTML | 2026-10-02, datacenter VM |

## Delivery (CDN)

| Surface | Status | Notes | Last verified |
|---|---|---|---|
| `*.cdninstagram.com` / `*.fbcdn.net` URLs as exposed in embed HTML | WORKING | unauthenticated GET; Content-Length present; JPEG magic verified | 2026-10-02, datacenter VM (live 33 KB JPEG) |

## Share links

| Surface | Status | Notes | Last verified |
|---|---|---|---|
| `instagram.com/share/...` | UNVERIFIED | one-hop expansion implemented; behavior varies by region/IP | — |

## Field observations

* The embed surface differentiates by **User-Agent**, not by login: a
  browser UA often gets the JS shell, while `facebookexternalhit` gets
  the SSR'd media HTML from the same IP.
* `ig_cache_key` on embed media URLs base64-encodes the numeric media id
  — a free, verifiable truth signal; the shortcode math cross-checks it.
* When a post is gone, the embed page says so in prose ("Sorry, this
  page isn't available") — that is the honest-empty signal.
