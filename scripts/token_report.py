"""Report total token spend across every benchmark run ever recorded.

    python scripts/token_report.py                      # totals + per-model breakdown
    python scripts/token_report.py --by month           # spend over time
    python scripts/token_report.py --as-of 2026-06-01   # price at an older price book
    python scripts/token_report.py --csv spend.csv      # full per-run ledger

Reports each run twice: at the price that was in force when it ran, and at
today's price for the same model. The gap between the two is what changed in
the market, not in the experiment.
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from token_ledger import (  # noqa: E402
    LEDGER_EXPORT_COLUMNS,
    PRICING_HISTORY_DIR,
    RESULTS_ROOT,
    available_price_snapshots,
    build_ledger,
    group_summary,
    load_price_book,
    resolve_price_book,
    summarize,
)

LEDGER_COLUMNS = LEDGER_EXPORT_COLUMNS


def _money(value):
    return "—" if value is None else "${:,.4f}".format(value)


def _tokens(value):
    return "{:,.0f}".format(value or 0)


def _resolve_price_book(as_of, prices):
    if not as_of:
        # Live prices are the default: "what would it cost now" has to mean the
        # rate the provider is charging now, not the last local sync.
        return resolve_price_book(
            prices,
            on_fallback=lambda exc: print(
                "Live OpenRouter prices unavailable ({}: {}); using the local "
                "registry instead.".format(type(exc).__name__, exc)
            ),
        )
    snapshots = available_price_snapshots()
    matching = [path for path in snapshots if as_of in os.path.basename(path)]
    if matching:
        return load_price_book(matching[-1])
    # No exact date: fall back to the newest snapshot at or before the request.
    earlier = [path for path in snapshots if os.path.basename(path)[-15:-5] <= as_of]
    if earlier:
        print(
            "No price book for {}; using {}".format(
                as_of, os.path.basename(earlier[-1])
            )
        )
        return load_price_book(earlier[-1])
    raise SystemExit(
        "No dated price book found in {}. Benchmarks archive one automatically, "
        "or run scripts/sync_openrouter.py; omit --as-of to use live prices."
        .format(PRICING_HISTORY_DIR)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=RESULTS_ROOT, help="Results root to scan.")
    parser.add_argument(
        "--by",
        default="model",
        choices=("model", "month", "task", "track", "provider"),
        help="Breakdown dimension (default: model).",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="Reprice against the dated price book for this YYYY-MM-DD instead of today's.",
    )
    parser.add_argument(
        "--prices",
        default="live",
        choices=("live", "local"),
        help=(
            "Where today's prices come from: 'live' reads the OpenRouter API "
            "(default), 'local' reads configs/benchmarks/models.json."
        ),
    )
    parser.add_argument("--csv", default=None, help="Write the full per-run ledger here.")
    parser.add_argument(
        "--min-cost",
        type=float,
        default=0.0,
        help="Hide breakdown rows below this historical spend.",
    )
    args = parser.parse_args()

    book = _resolve_price_book(args.as_of, args.prices)
    rows = build_ledger(args.results, book)
    if not rows:
        raise SystemExit("No benchmark runs found under {}".format(args.results))

    totals = summarize(rows)
    reference = book.get("synced_at") or book.get("source") or "current price list"

    print("\n=== Token spend across {} runs ===".format(totals["runs"]))
    print("Prompt tokens      : {}".format(_tokens(totals["prompt_tokens"])))
    print("Completion tokens  : {}".format(_tokens(totals["completion_tokens"])))
    if totals["reasoning_tokens"]:
        print("  of which reasoning: {}".format(_tokens(totals["reasoning_tokens"])))
    if totals["cached_prompt_tokens"]:
        print("  cached prompt     : {}".format(_tokens(totals["cached_prompt_tokens"])))
    print("Total tokens       : {}".format(_tokens(totals["total_tokens"])))
    print()
    print("Cost at the time   : {} ({} of {} runs priced)".format(
        _money(totals["cost_then_usd"]), totals["runs_priced_then"], totals["runs"]))
    print("Cost at {:<10} : {} ({} of {} runs priced)".format(
        str(reference), _money(totals["cost_now_usd"]),
        totals["runs_priced_now"], totals["runs"]))
    if totals["price_change_pct"] is not None:
        print(
            "Like-for-like      : {} then vs {} now over {} comparable runs "
            "({:+.1f}%)".format(
                _money(totals["comparable_cost_then_usd"]),
                _money(totals["comparable_cost_now_usd"]),
                totals["comparable_runs"],
                totals["price_change_pct"],
            )
        )
    if totals["runs_with_tokens"] < totals["runs"]:
        print(
            "\nNote: {} run(s) carry no token accounting (client errors, or runs "
            "recorded before usage was captured) and contribute zero tokens.".format(
                totals["runs"] - totals["runs_with_tokens"]
            )
        )

    print("\n--- By {} ---".format(args.by))
    header = "{:<38} {:>7} {:>14} {:>12} {:>12} {:>9}".format(
        args.by, "runs", "tokens", "then", "now", "priced")
    print(header)
    print("-" * len(header))
    for group in group_summary(rows, args.by):
        if group["cost_then_usd"] < args.min_cost:
            continue
        # A group with no priced run is unknown, not free: never print $0 there.
        then = _money(group["cost_then_usd"]) if group["runs_priced_then"] else "n/a"
        now = _money(group["cost_now_usd"]) if group["runs_priced_now"] else "n/a"
        print("{:<38} {:>7} {:>14} {:>12} {:>12} {:>9}".format(
            group[args.by][:38],
            group["runs"],
            _tokens(group["total_tokens"]),
            then,
            now,
            "{}/{}".format(group["runs_priced_then"], group["runs"]),
        ))
    print(
        "\n'priced' counts runs carrying the price list they ran under. Runs "
        "recorded before price snapshots existed show n/a for 'then' - their "
        "tokens still count, only the historical rate is unknown."
    )

    if args.csv:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key) for key in LEDGER_COLUMNS})
        print("\nPer-run ledger written to {}".format(args.csv))


if __name__ == "__main__":
    main()
