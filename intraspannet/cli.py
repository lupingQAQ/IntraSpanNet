"""Command-line interface for IntraSpanNet."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

from . import __version__
from .inference import DEFAULT_THRESHOLD, Ensemble
from .preprocess import FLOW_LEN


def _print_rows(rows: list[dict], limit: int = 50) -> None:
    print(f"{'source':24s} {'tier':10s} {'type':22s} {'product':26s} {'dist':>7s} {'conf':>6s}")
    print("-" * 100)
    for row in rows[:limit]:
        print(
            f"{row.get('source', '-'):24s} "
            f"{row['tier']:10s} "
            f"{row['type']:22s} "
            f"{row['product']:26s} "
            f"{row['distance']:7.4f} "
            f"{row['confidence']:6.3f}"
        )
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more")


def _summary(rows: list[dict]) -> None:
    print("\n=== product summary ===")
    for name, count in Counter(row["product"] for row in rows).most_common():
        print(f"  {name}: {count}")
    print("\n=== tier summary ===")
    for name, count in Counter(row["tier"] for row in rows).most_common():
        print(f"  {name}: {count}")


def _arms_kwargs(args: argparse.Namespace) -> dict:
    """Optional arm override, useful for a quick single-arm CPU run."""
    kw = {}
    if getattr(args, "arms", ""):
        kw["arms"] = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    if getattr(args, "gate", ""):
        kw["gate"] = tuple(a.strip() for a in args.gate.split(",") if a.strip())
    return kw


def cmd_classify(args: argparse.Namespace) -> int:
    engine = Ensemble.from_config(
        args.weights_dir,
        threshold=args.threshold,
        device=args.device,
        batch_size=args.batch,
        **_arms_kwargs(args),
    )
    if args.flow_dir:
        rows = engine.classify_flow_dir(args.flow_dir, topk=args.topk)
    else:
        rows = engine.classify_paths(args.pcap, min_pkts=args.min_pkts, topk=args.topk)

    _print_rows(rows, limit=args.limit)
    _summary(rows)
    print(f"\nconfig: {json.dumps(engine.config, ensure_ascii=False)}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=2)
        print(f"wrote {args.json}")
    return 0


def _parse_flow_records(body: bytes) -> np.ndarray:
    records = []
    for off in range(0, len(body) - 1619, 1620):
        raw = body[off : off + 1620]
        if raw[:4] == b"FLW1":
            records.append(np.frombuffer(raw[20:1620], dtype=np.uint8))
    if not records:
        return np.zeros((0, FLOW_LEN), dtype=np.uint8)
    return np.stack(records)


def cmd_serve(args: argparse.Namespace) -> int:
    engine = Ensemble.from_config(
        args.weights_dir,
        threshold=args.threshold,
        device=args.device,
        batch_size=args.batch,
        **_arms_kwargs(args),
    )

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            flows = _parse_flow_records(body)
            rows = engine.classify(flows) if len(flows) else []
            payload = json.dumps(rows, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):  # silence per-request logs
            return

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"serving on http://{args.host}:{args.port} (POST / with FLW1 records)")
    print(f"config: {json.dumps(engine.config, ensure_ascii=False)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="intraspannet", description="IntraSpanNet traffic classifier")
    parser.add_argument("--version", action="version", version=f"intraspannet {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    classify = sub.add_parser("classify", help="classify pcap files or 1600-byte flow bins")
    classify.add_argument("--weights-dir", required=True, help="directory with stage3_*.pth and prototypes")
    classify.add_argument("--pcap", nargs="+", default=[], help="pcap/pcapng files or glob patterns")
    classify.add_argument("--flow-dir", default="", help="directory containing flow_*.bin")
    classify.add_argument("--device", default=None, help="cuda or cpu; cpu uses the slower PyTorch reference path")
    classify.add_argument("--batch", type=int, default=64)
    classify.add_argument("--min-pkts", type=int, default=1)
    classify.add_argument("--topk", type=int, default=3)
    classify.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    classify.add_argument("--limit", type=int, default=50)
    classify.add_argument("--json", default="", help="write full results to this JSON file")
    classify.add_argument("--arms", default="", help="comma-separated classifier arms, e.g. a_s0 (default: all four)")
    classify.add_argument("--gate", default="", help="comma-separated gate arms, e.g. a_s0 (default: a_lda,b_lda)")
    classify.set_defaults(func=cmd_classify)

    serve = sub.add_parser("serve", help="HTTP service for FLW1 records")
    serve.add_argument("--weights-dir", required=True)
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=9012)
    serve.add_argument("--device", default=None)
    serve.add_argument("--batch", type=int, default=64)
    serve.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    serve.add_argument("--arms", default="")
    serve.add_argument("--gate", default="")
    serve.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows consoles default to a legacy code page that cannot encode the
    # Chinese tier names, which would abort the table halfway through.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "classify" and not args.pcap and not args.flow_dir:
        parser.error("classify requires --pcap or --flow-dir")
    try:
        return args.func(args)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
