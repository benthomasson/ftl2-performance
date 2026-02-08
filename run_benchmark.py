#!/usr/bin/env python3
"""Run FTL2 vs Ansible benchmarks side by side.

Uses separate virtual environments for Ansible and FTL2 because FTL2
modifies the Ansible package — they cannot coexist in the same venv.

Setup:
    python3 run_benchmark.py --setup

Usage:
    python3 run_benchmark.py                     # run all benchmarks
    python3 run_benchmark.py uri_get             # run one benchmark
    python3 run_benchmark.py uri_get --runs 5    # run with custom iteration count
    python3 run_benchmark.py --list              # list available benchmarks
"""

import argparse
import importlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).parent
BENCHMARKS_DIR = ROOT_DIR / "benchmarks"
ANSIBLE_VENV = ROOT_DIR / ".venv-ansible"
FTL2_VENV = ROOT_DIR / ".venv-ftl2"


def get_venv_python(venv: Path) -> Path:
    return venv / "bin" / "python"


def get_ansible_playbook() -> Path:
    return ANSIBLE_VENV / "bin" / "ansible-playbook"


def check_venvs() -> tuple[bool, bool]:
    """Check if both venvs exist and have their packages."""
    ansible_ok = get_ansible_playbook().exists()
    ftl2_ok = get_venv_python(FTL2_VENV).exists()
    return ansible_ok, ftl2_ok


def setup_venvs():
    """Create both virtual environments."""
    import venv

    # --- Ansible venv ---
    if not ANSIBLE_VENV.exists():
        print(f"Creating Ansible venv at {ANSIBLE_VENV}...")
        venv.create(str(ANSIBLE_VENV), with_pip=True)
    else:
        print(f"Ansible venv exists at {ANSIBLE_VENV}")

    print("Installing ansible-core...")
    subprocess.run(
        [str(get_venv_python(ANSIBLE_VENV)), "-m", "pip", "install", "-q", "ansible-core"],
        check=True,
    )

    # --- FTL2 venv ---
    if not FTL2_VENV.exists():
        print(f"Creating FTL2 venv at {FTL2_VENV}...")
        venv.create(str(FTL2_VENV), with_pip=True)
    else:
        print(f"FTL2 venv exists at {FTL2_VENV}")

    # Install ftl2 in editable mode from the sibling repo
    ftl2_repo = Path.home() / "git" / "faster-than-light2"
    if not ftl2_repo.exists():
        print(f"ERROR: FTL2 repo not found at {ftl2_repo}")
        print("  Clone it or set FTL2_REPO env var")
        sys.exit(1)

    print(f"Installing ftl2 from {ftl2_repo}...")
    subprocess.run(
        [str(get_venv_python(FTL2_VENV)), "-m", "pip", "install", "-q", "-e", str(ftl2_repo)],
        check=True,
    )

    print("\nSetup complete:")
    print(f"  Ansible: {get_ansible_playbook()}")
    print(f"  FTL2:    {get_venv_python(FTL2_VENV)}")


def discover_benchmarks() -> list[str]:
    """Find all benchmark modules in the benchmarks directory."""
    benchmarks = []
    for p in sorted(BENCHMARKS_DIR.iterdir()):
        if p.is_dir() and (p / "bench.py").exists():
            benchmarks.append(p.name)
    return benchmarks


def run_ansible_playbook(playbook: Path, inventory: str = "localhost,") -> tuple[bool, float, str]:
    """Run an Ansible playbook and return (success, elapsed_seconds, stderr)."""
    start = time.perf_counter()
    result = subprocess.run(
        [str(get_ansible_playbook()), str(playbook), "-i", inventory, "-c", "local"],
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start
    return result.returncode == 0, elapsed, result.stderr


def run_ftl2_script(script: Path) -> tuple[bool, float, str]:
    """Run an FTL2 script and return (success, elapsed_seconds, stderr)."""
    start = time.perf_counter()
    result = subprocess.run(
        [str(get_venv_python(FTL2_VENV)), str(script)],
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start
    return result.returncode == 0, elapsed, result.stderr


def run_benchmark(name: str, runs: int = 3) -> dict:
    """Run a single benchmark, returning timing results."""
    bench_dir = BENCHMARKS_DIR / name

    if not bench_dir.exists():
        print(f"Benchmark not found: {name}")
        sys.exit(1)

    # Import the benchmark module for metadata
    spec = importlib.util.spec_from_file_location(f"bench_{name}", bench_dir / "bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    description = getattr(mod, "DESCRIPTION", name)
    print(f"\n{'=' * 60}")
    print(f"  {name}: {description}")
    print(f"  {runs} run(s) each")
    print(f"{'=' * 60}")

    results = {"name": name, "description": description, "runs": runs}

    # --- Ansible ---
    playbook = bench_dir / "playbook.yml"
    if playbook.exists():
        ansible_times = []
        inventory = str(bench_dir / "inventory") if (bench_dir / "inventory").exists() else "localhost,"
        for i in range(runs):
            success, elapsed, stderr = run_ansible_playbook(playbook, inventory)
            status = "ok" if success else "FAIL"
            print(f"  Ansible  run {i+1}/{runs}: {elapsed:.3f}s [{status}]")
            if not success and i == 0:
                # Show first failure's stderr for debugging
                for line in stderr.strip().splitlines()[-3:]:
                    print(f"           {line}")
            if success:
                ansible_times.append(elapsed)
        if ansible_times:
            results["ansible"] = {
                "times": ansible_times,
                "mean": sum(ansible_times) / len(ansible_times),
                "min": min(ansible_times),
                "max": max(ansible_times),
            }
        else:
            results["ansible"] = {"error": "all runs failed"}
    else:
        print("  Ansible: no playbook.yml found, skipping")

    # --- FTL2 ---
    ftl2_script = bench_dir / "ftl2_script.py"
    if ftl2_script.exists():
        ftl2_times = []
        for i in range(runs):
            success, elapsed, stderr = run_ftl2_script(ftl2_script)
            status = "ok" if success else "FAIL"
            print(f"  FTL2     run {i+1}/{runs}: {elapsed:.3f}s [{status}]")
            if not success and i == 0:
                for line in stderr.strip().splitlines()[-3:]:
                    print(f"           {line}")
            if success:
                ftl2_times.append(elapsed)
        if ftl2_times:
            results["ftl2"] = {
                "times": ftl2_times,
                "mean": sum(ftl2_times) / len(ftl2_times),
                "min": min(ftl2_times),
                "max": max(ftl2_times),
            }
        else:
            results["ftl2"] = {"error": "all runs failed"}
    else:
        print("  FTL2: no ftl2_script.py found, skipping")

    # --- Summary ---
    if "mean" in results.get("ansible", {}) and "mean" in results.get("ftl2", {}):
        speedup = results["ansible"]["mean"] / results["ftl2"]["mean"]
        print(f"\n  Ansible mean: {results['ansible']['mean']:.3f}s")
        print(f"  FTL2    mean: {results['ftl2']['mean']:.3f}s")
        print(f"  Speedup:      {speedup:.1f}x")
        results["speedup"] = round(speedup, 2)

    return results


def main():
    parser = argparse.ArgumentParser(description="FTL2 vs Ansible benchmarks")
    parser.add_argument("benchmarks", nargs="*", help="Benchmark names to run (default: all)")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per benchmark (default: 3)")
    parser.add_argument("--list", action="store_true", help="List available benchmarks")
    parser.add_argument("--json", type=str, metavar="FILE", help="Write results to JSON file")
    parser.add_argument("--setup", action="store_true", help="Create venvs and install dependencies")
    args = parser.parse_args()

    if args.setup:
        setup_venvs()
        return

    if args.list:
        available = discover_benchmarks()
        print("Available benchmarks:")
        for name in available:
            bench_dir = BENCHMARKS_DIR / name
            spec = importlib.util.spec_from_file_location(f"bench_{name}", bench_dir / "bench.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            desc = getattr(mod, "DESCRIPTION", "")
            print(f"  {name:30s} {desc}")
        return

    # Check venvs exist
    ansible_ok, ftl2_ok = check_venvs()
    if not ansible_ok or not ftl2_ok:
        missing = []
        if not ansible_ok:
            missing.append("Ansible")
        if not ftl2_ok:
            missing.append("FTL2")
        print(f"Missing venv(s): {', '.join(missing)}")
        print(f"Run: python3 {__file__} --setup")
        sys.exit(1)

    available = discover_benchmarks()
    to_run = args.benchmarks or available
    if not to_run:
        print("No benchmarks found. Create one in benchmarks/<name>/bench.py")
        return

    all_results = []
    for name in to_run:
        result = run_benchmark(name, runs=args.runs)
        all_results.append(result)

    # Final summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    print(f"  {'Benchmark':<30s} {'Ansible':>10s} {'FTL2':>10s} {'Speedup':>10s}")
    print(f"  {'-'*30:<30s} {'-'*10:>10s} {'-'*10:>10s} {'-'*10:>10s}")
    for r in all_results:
        ansible_t = f"{r['ansible']['mean']:.3f}s" if "mean" in r.get("ansible", {}) else "n/a"
        ftl2_t = f"{r['ftl2']['mean']:.3f}s" if "mean" in r.get("ftl2", {}) else "n/a"
        speedup = f"{r['speedup']:.1f}x" if "speedup" in r else "n/a"
        print(f"  {r['name']:<30s} {ansible_t:>10s} {ftl2_t:>10s} {speedup:>10s}")

    if args.json:
        Path(args.json).write_text(json.dumps(all_results, indent=2) + "\n")
        print(f"\nResults written to {args.json}")


if __name__ == "__main__":
    main()
