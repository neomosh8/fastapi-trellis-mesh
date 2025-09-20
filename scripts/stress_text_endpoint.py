#!/usr/bin/env python3
"""Mixed concurrency stress test for the text-to-mesh endpoint."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional


@dataclass
class RequestPlan:
    index: int
    prompt: str
    seed: int
    delay_before_send: float


@dataclass
class RequestResult:
    index: int
    prompt: str
    seed: int
    delay_before_send: float
    start_offset: float
    duration: float
    status: Optional[int]
    response_bytes: int
    digest: Optional[str]
    error: Optional[str]


def issue_request(
    plan: RequestPlan,
    url: str,
    timeout: float,
    test_start: float,
) -> RequestResult:
    if plan.delay_before_send > 0:
        time.sleep(plan.delay_before_send)

    start = time.perf_counter()
    start_offset = start - test_start
    payload = json.dumps({"prompt": plan.prompt, "seed": plan.seed}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        duration = time.perf_counter() - start
        detail = exc.read().decode("utf-8", "replace")
        return RequestResult(
            index=plan.index,
            prompt=plan.prompt,
            seed=plan.seed,
            delay_before_send=plan.delay_before_send,
            start_offset=start_offset,
            duration=duration,
            status=exc.code,
            response_bytes=0,
            digest=None,
            error=detail.strip(),
        )
    except urllib.error.URLError as exc:
        duration = time.perf_counter() - start
        return RequestResult(
            index=plan.index,
            prompt=plan.prompt,
            seed=plan.seed,
            delay_before_send=plan.delay_before_send,
            start_offset=start_offset,
            duration=duration,
            status=None,
            response_bytes=0,
            digest=None,
            error=str(exc.reason),
        )

    duration = time.perf_counter() - start
    digest = sha256(body).hexdigest() if body else None
    return RequestResult(
        index=plan.index,
        prompt=plan.prompt,
        seed=plan.seed,
        delay_before_send=plan.delay_before_send,
        start_offset=start_offset,
        duration=duration,
        status=status,
        response_bytes=len(body),
        digest=digest,
        error=None,
    )


def build_plan(total: int, initial_burst: int, min_delay: float, max_delay: float) -> list[RequestPlan]:
    prompts = [
        "a weathered wooden treasure chest with brass accents",
        "a futuristic sci-fi motorcycle with glowing blue lights",
        "an ancient stone statue of a dragon coiled around a pillar",
        "a cozy armchair made of soft leather with metal studs",
        "a crystalline magic staff emitting purple energy",
        "a sleek modern coffee table with glass top",
        "a whimsical treehouse with rope bridges",
        "a detailed pirate cannon on a wooden carriage",
    ]

    plan: list[RequestPlan] = []
    seeds = random.sample(range(1, 10_000), k=total)

    for i in range(total):
        if i < initial_burst:
            delay = 0.0
        else:
            delay = random.uniform(min_delay, max_delay)
        prompt = random.choice(prompts)
        plan.append(RequestPlan(index=i, prompt=prompt, seed=seeds[i], delay_before_send=delay))

    random.shuffle(plan)
    return plan


def format_seconds(value: float) -> str:
    return f"{value:.2f}s"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Stress test the text-to-mesh endpoint")
    parser.add_argument("--url", required=True, help="Endpoint URL")
    parser.add_argument("--requests", type=int, default=6, help="Total number of requests to send")
    parser.add_argument(
        "--initial-burst",
        type=int,
        default=3,
        help="Number of requests sent immediately to simulate simultaneity",
    )
    parser.add_argument("--min-delay", type=float, default=1.0, help="Minimum stagger delay in seconds")
    parser.add_argument("--max-delay", type=float, default=15.0, help="Maximum stagger delay in seconds")
    parser.add_argument("--timeout", type=float, default=600.0, help="Per-request timeout")
    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Thread pool size (default matches total requests)",
    )

    args = parser.parse_args(argv)

    if args.requests <= 0:
        print("Nothing to do: requests must be > 0", file=sys.stderr)
        return 1

    total = args.requests
    initial_burst = min(args.initial_burst, total)
    workers = max(1, min(args.workers, total))

    plan = build_plan(total=total, initial_burst=initial_burst, min_delay=args.min_delay, max_delay=args.max_delay)
    print(f"Planning {total} requests (initial burst {initial_burst}, workers {workers})")

    for item in sorted(plan, key=lambda x: x.index):
        print(
            f"  req#{item.index:02d}: delay={item.delay_before_send:.2f}s seed={item.seed} prompt='{item.prompt[:48]}{'…' if len(item.prompt) > 48 else ''}'"
        )

    test_start = time.perf_counter()
    results: list[RequestResult] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_plan: dict[Future[RequestResult], RequestPlan] = {}
        for item in plan:
            future = executor.submit(issue_request, item, args.url, args.timeout, test_start)
            future_to_plan[future] = item

        for future in as_completed(future_to_plan):
            result = future.result()
            results.append(result)
            status_text = result.status if result.status is not None else "ERR"
            print(
                f"Done req#{result.index:02d}: status={status_text} start@{format_seconds(result.start_offset)} "
                f"took {format_seconds(result.duration)} bytes={result.response_bytes}"
            )
            if result.error:
                print(f"    error: {result.error}")

    if not results:
        print("No results captured.")
        return 1

    results.sort(key=lambda r: r.start_offset)

    durations = [r.duration for r in results if r.status == 200]
    total_runtime = time.perf_counter() - test_start

    print("\n=== Summary ===")
    print(f"Total runtime: {format_seconds(total_runtime)} for {len(results)} requests")

    if durations:
        avg = sum(durations) / len(durations)
        print(
            f"Successful requests: {len(durations)} | min {format_seconds(min(durations))} "
            f"avg {format_seconds(avg)} max {format_seconds(max(durations))}"
        )
    else:
        print("No successful requests.")

    print("\nPer-request detail:")
    for r in results:
        status_text = r.status if r.status is not None else "ERR"
        digest = r.digest[:12] if r.digest else "-"
        print(
            f"  req#{r.index:02d} start@{format_seconds(r.start_offset)} delay={r.delay_before_send:.2f}s "
            f"status={status_text} dur={format_seconds(r.duration)} bytes={r.response_bytes} digest={digest}"
        )
        print(f"    prompt='{r.prompt}' seed={r.seed}")
        if r.error:
            print(f"    error: {r.error}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
