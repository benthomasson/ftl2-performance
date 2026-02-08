#!/usr/bin/env python3
"""Generate charts from benchmark results.

Usage:
    python3 generate_charts.py                        # uses results.json
    python3 generate_charts.py --input custom.json
    python3 generate_charts.py --output-dir charts/

Requires matplotlib (installed in .venv-ftl2).
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


# FTL2 brand-ish colors
COLOR_ANSIBLE = "#EE0000"
COLOR_FTL2 = "#2196F3"
COLOR_SPEEDUP = "#4CAF50"
BG_COLOR = "#FAFAFA"


def load_results(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    # Filter to benchmarks that have both sides
    return [r for r in data if "mean" in r.get("ansible", {}) and "mean" in r.get("ftl2", {})]


def chart_comparison_bars(results: list[dict], output_dir: Path):
    """Side-by-side bar chart: Ansible vs FTL2 execution time."""
    names = [r["name"].replace("_", " ").title() for r in results]
    ansible_times = [r["ansible"]["mean"] for r in results]
    ftl2_times = [r["ftl2"]["mean"] for r in results]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    x = range(len(names))
    bar_width = 0.35

    bars_a = ax.bar([i - bar_width/2 for i in x], ansible_times, bar_width,
                     label="Ansible", color=COLOR_ANSIBLE, edgecolor="white", linewidth=0.5)
    bars_f = ax.bar([i + bar_width/2 for i in x], ftl2_times, bar_width,
                     label="FTL2", color=COLOR_FTL2, edgecolor="white", linewidth=0.5)

    # Value labels on bars
    for bar in bars_a:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f"{bar.get_height():.2f}s", ha="center", va="bottom", fontsize=10, fontweight="bold")
    for bar in bars_f:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                f"{bar.get_height():.2f}s", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_ylabel("Execution Time (seconds)", fontsize=12)
    ax.set_title("FTL2 vs Ansible — Execution Time", fontsize=14, fontweight="bold", pad=15)
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, fontsize=11)
    ax.legend(fontsize=11, loc="upper left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, max(ansible_times) * 1.25)

    plt.tight_layout()
    out = output_dir / "comparison.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {out}")


def chart_speedup(results: list[dict], output_dir: Path):
    """Horizontal bar chart showing speedup factor."""
    names = [r["name"].replace("_", " ").title() for r in results]
    speedups = [r["speedup"] for r in results]

    # Sort by speedup
    paired = sorted(zip(speedups, names), reverse=True)
    speedups, names = zip(*paired)

    fig, ax = plt.subplots(figsize=(8, max(3, len(names) * 1.2)))
    fig.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    bars = ax.barh(range(len(names)), speedups, color=COLOR_SPEEDUP,
                    edgecolor="white", linewidth=0.5, height=0.6)

    # Value labels
    for bar, s in zip(bars, speedups):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"{s:.1f}x", ha="left", va="center", fontsize=13, fontweight="bold")

    # Reference line at 1x
    ax.axvline(x=1, color="#999", linestyle="--", linewidth=0.8, alpha=0.7)

    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=12)
    ax.set_xlabel("Speedup Factor (higher is better)", fontsize=12)
    ax.set_title("FTL2 Speedup over Ansible", fontsize=14, fontweight="bold", pad=15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(0, max(speedups) * 1.3)
    ax.invert_yaxis()

    plt.tight_layout()
    out = output_dir / "speedup.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {out}")


def chart_individual_runs(results: list[dict], output_dir: Path):
    """Per-benchmark scatter/strip plot showing individual run times."""
    n = len(results)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4), sharey=False)
    fig.set_facecolor(BG_COLOR)

    if n == 1:
        axes = [axes]

    for ax, r in zip(axes, results):
        ax.set_facecolor(BG_COLOR)
        name = r["name"].replace("_", " ").title()

        ansible_times = r["ansible"]["times"]
        ftl2_times = r["ftl2"]["times"]

        # Strip plot with jitter
        import random
        random.seed(42)
        jitter = 0.08

        ax.scatter([1 + random.uniform(-jitter, jitter) for _ in ansible_times],
                   ansible_times, color=COLOR_ANSIBLE, s=60, zorder=3, alpha=0.8, edgecolors="white", linewidth=0.5)
        ax.scatter([2 + random.uniform(-jitter, jitter) for _ in ftl2_times],
                   ftl2_times, color=COLOR_FTL2, s=60, zorder=3, alpha=0.8, edgecolors="white", linewidth=0.5)

        # Mean lines
        ax.hlines(r["ansible"]["mean"], 0.7, 1.3, color=COLOR_ANSIBLE, linewidth=2, alpha=0.6)
        ax.hlines(r["ftl2"]["mean"], 1.7, 2.3, color=COLOR_FTL2, linewidth=2, alpha=0.6)

        ax.set_xticks([1, 2])
        ax.set_xticklabels(["Ansible", "FTL2"], fontsize=10)
        ax.set_title(name, fontsize=11, fontweight="bold")
        ax.set_ylabel("Time (s)", fontsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlim(0.4, 2.6)

    fig.suptitle("Individual Run Times", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = output_dir / "runs.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  {out}")


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark charts")
    parser.add_argument("--input", type=str, default="results.json", help="Results JSON file")
    parser.add_argument("--output-dir", type=str, default="charts", help="Output directory for PNGs")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Results file not found: {input_path}")
        print("Run benchmarks first: python3 run_benchmark.py --json results.json")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    results = load_results(input_path)
    if not results:
        print("No valid benchmark results found")
        sys.exit(1)

    print("Generating charts:")
    chart_comparison_bars(results, output_dir)
    chart_speedup(results, output_dir)
    chart_individual_runs(results, output_dir)
    print(f"\nDone — {len(results)} benchmarks, 3 charts in {output_dir}/")


if __name__ == "__main__":
    main()
