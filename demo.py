#!/usr/bin/env python3
"""
demo.py — consume igagent exactly the way an external AI agent would
=====================================================================
Runs the CLI as a subprocess (`--json --quiet`, the machine contract),
then pretty-prints the manifest it points to.  No imports from the tool
itself — this file is proof that the subprocess+JSON contract is enough.

Usage:
    python demo.py <instagram_url_or_shortcode> [--out demo_output]
                   [--skip-download] [--raw]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOL = ROOT / "igagent.py"


def main() -> int:
    ap = argparse.ArgumentParser(description="igagent end-user demo")
    ap.add_argument("url", help="Instagram post URL or shortcode")
    ap.add_argument("--out", default="demo_output")
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--raw", action="store_true",
                    help="dump the raw envelope JSON and exit")
    args = ap.parse_args()

    cmd = [sys.executable, str(TOOL), args.url, "--out", args.out,
           "--json", "--quiet"]
    if args.skip_download:
        cmd.append("--no-download")

    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        summary = json.loads(proc.stdout)
    except ValueError:
        print("demo failed: CLI produced no parsable stdout. "
              f"stderr tail:\n{(proc.stderr or '')[-800:]}", file=sys.stderr)
        return 1

    if not summary.get("ok"):
        print(json.dumps(summary, indent=2))
        return proc.returncode or 1

    manifest = Path(summary["manifest_path"])
    envelope = json.loads(manifest.read_text(encoding="utf-8"))
    if args.raw:
        print(json.dumps(envelope, indent=2, ensure_ascii=False))
        return 0

    post = envelope.get("post") or {}
    meta = envelope.get("metadata") or {}
    author = post.get("author") or {}

    print()
    bar = "─" * 62
    print(bar)
    status = envelope.get("status")
    icon = {"ok": "✓", "partial": "~", "empty": "✗"}.get(status, "?")
    print(f" {icon} igagent run: {status.upper()}"
          f"   (decoded via: {post.get('extraction_source')})")
    print(bar)
    print(f"  post      : {post.get('url')}")
    print(f"  media_id  : {post.get('media_id')}")
    print(f"  type      : {post.get('type')}   kind: {post.get('kind')}")
    print(f"  author    : @{author.get('username') or '?'}"
          + (f"  ({author.get('followers'):,} followers)"
             if author.get("followers") else ""))
    print(f"  created   : {post.get('created_at') or 'not exposed'}")
    cap = post.get("caption")
    if cap:
        cap = cap if len(cap) <= 80 else cap[:77] + "..."
        print(f"  caption   : {cap}")
    print(f"  carousel  : known={ (post.get('carousel') or {}).get('known') }"
          f"  children={ (post.get('carousel') or {}).get('child_count') }")
    print(bar)
    media = post.get("media") or {}
    for img in media.get("images", []):
        state = "saved" if img.get("downloaded") else \
                (f"not saved: {img.get('reason')}" if img.get("reason") else "url only")
        print(f"  [img ] {img.get('file') or '(no file)'} — {state}")
    for vid in media.get("videos", []):
        state = "saved" if vid.get("downloaded") else \
                (f"not saved: {vid.get('reason')}" if vid.get("reason") else "url only")
        print(f"  [vid ] {vid.get('file') or '(no file)'} — {state}")
    counts = meta.get("counts") or {}
    print(bar)
    print(f"  totals    : {counts.get('images', 0)} image(s), "
          f"{counts.get('videos', 0)} video(s), "
          f"{counts.get('downloaded_media', 0)} downloaded, "
          f"{counts.get('failed_downloads', 0)} failed "
          f"in {meta.get('duration_sec', 0):.1f}s")
    slots = ", ".join(f"{s.get('slot')}={s.get('outcome')}"
                      for s in meta.get("decode_slots_tried", []))
    print(f"  slots     : {slots}")
    print(f"  manifest  : {manifest}")
    print(bar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
