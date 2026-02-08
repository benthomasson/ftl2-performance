# CLAUDE.md

## Repository Overview

FTL2 vs Ansible performance benchmark suite. Each benchmark has an Ansible playbook and an equivalent FTL2 script that are timed side by side using separate virtual environments.

## Key Constraint

Ansible and FTL2 cannot share a virtual environment. FTL2 modifies the Ansible package at import time, so loading both in the same process produces incorrect results. The runner invokes each side with its own venv's Python interpreter.

## Project Structure

```
run_benchmark.py              # benchmark runner (no dependencies beyond stdlib)
benchmarks/
    <name>/
        bench.py              # DESCRIPTION = "..." metadata
        playbook.yml          # Ansible version
        ftl2_script.py        # FTL2 version
.venv-ansible/                # clean ansible-core (gitignored)
.venv-ftl2/                   # ftl2 editable install (gitignored)
```

## Commands

```bash
python3 run_benchmark.py --setup          # create venvs, install deps
python3 run_benchmark.py --list           # list benchmarks
python3 run_benchmark.py                  # run all
python3 run_benchmark.py <name> --runs 5  # run one benchmark
python3 run_benchmark.py --json out.json  # save results
```

## Writing Benchmarks

- Each benchmark is a directory under `benchmarks/` with `bench.py`, `playbook.yml`, and `ftl2_script.py`
- The Ansible playbook should use `hosts: localhost`, `connection: local`, `gather_facts: false` (unless testing fact gathering)
- The FTL2 script should use `from ftl2 import automation` and `async with automation() as ftl:`
- Both sides should do the same work — create equivalent operations, not just "similar" ones
- Clean up after yourself (remove temp files in the benchmark itself)
- The runner handles timing — scripts should just do the work and exit

## Guidelines for New Benchmarks

Good benchmark candidates:
- Operations that scale with task count (file, copy, template, command)
- Module types with FTL-native implementations (uri, get_url, stat, file)
- Mixed workloads that combine multiple module types
- Fact gathering and variable resolution overhead

Keep benchmarks self-contained — no external dependencies, no network calls, no root required. All operations should run locally against /tmp.
