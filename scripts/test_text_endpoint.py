#!/usr/bin/env python3
"""Simple on-demand test for the text-to-mesh endpoint."""

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
from hashlib import sha256


def run(url: str, prompt: str, seed: int, timeout: float, output: pathlib.Path) -> int:
    payload = {"prompt": prompt, "seed": seed}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"POST {url}")
    print(f"Prompt: {prompt!r} (seed={seed})")

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            headers = dict(response.headers.items())
            body = response.read()
    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - start
        print(f"HTTP {exc.code} after {elapsed:.2f}s")
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:  # pragma: no cover - defensive
            detail = "<unable to decode body>"
        print(detail.strip())
        return 1
    except urllib.error.URLError as exc:
        elapsed = time.perf_counter() - start
        print(f"Request failed after {elapsed:.2f}s: {exc.reason}")
        return 1

    elapsed = time.perf_counter() - start
    digest = sha256(body).hexdigest()

    print(f"HTTP {status} in {elapsed:.2f}s")
    print(f"Response bytes: {len(body)} (sha256 {digest})")
    if headers.get("content-type"):
        print(f"Content-Type: {headers['content-type']}")

    if body:
        output.write_bytes(body)
        print(f"Saved GLB to {output}")

    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Smoke test for text-to-mesh endpoint")
    parser.add_argument("--url", required=True, help="Endpoint URL, e.g. http://host/generate_mesh_from_text")
    parser.add_argument("--prompt", required=True, help="Prompt to send")
    parser.add_argument("--seed", type=int, default=1, help="Seed value (default: 1)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="Request timeout in seconds (default: 600)",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("text_to_mesh_output.glb"),
        help="Where to store the response GLB",
    )

    args = parser.parse_args(argv)
    return run(args.url, args.prompt, args.seed, args.timeout, args.output)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
