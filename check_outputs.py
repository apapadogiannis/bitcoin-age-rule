#!/usr/bin/env python3
"""Reruns the pipeline and checks that every stored result is reproduced.

    python3 check_outputs.py                 # rerun ./run_all.sh, then compare
    python3 check_outputs.py --no-run        # compare the current files with the last commit (needs git)
    python3 check_outputs.py --also FILE     # also check a result file kept outside outputs/

What is compared: every text result file stored in outputs/ (.csv, .json, .tex, .txt), plus any
file named with --also. The stored copies are set aside, ./run_all.sh regenerates them, and the
two versions are compared number by number.

Why not character by character: the last digits of a floating-point result depend on the
processor (for example whether it has AVX-512) and on the build of the numerical libraries, so
two correct runs on different machines can differ in the 12th to 16th significant digit. A number
is accepted as reproduced when

  * the two texts are identical, or
  * the values agree to a relative tolerance of 1e-9 (absolute 1e-12 near zero), or
  * both were printed with the same fixed number of decimals and differ by at most one unit in
    the last printed place (a rounding flip caused by a last-digit difference).

Everything that is not a number (headers, labels, dates written as text) and every whole number
(counts, years) must match exactly. Exit status 0 if all results are reproduced, 1 otherwise.
Standard library only.
"""
import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXTENSIONS = (".csv", ".json", ".tex", ".txt")
NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
RTOL, ATOL = 1e-9, 1e-12


def git(*args):
    """Output of a git command run in the repository, or None if git or the repository is missing."""
    try:
        r = subprocess.run(["git", *args], cwd=HERE, capture_output=True)
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def machine():
    """Processor name, to tell apart runs on different machines in a log."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    import platform
    return platform.processor() or platform.machine()


def stored_files(also):
    """Result files to check: tracked files if this is a git checkout, otherwise all that exist."""
    tracked = git("ls-files", "outputs")
    if tracked is not None:
        names = tracked.decode().splitlines()
    else:
        names = [os.path.relpath(os.path.join(d, f), HERE).replace(os.sep, "/")
                 for d, _, fs in os.walk(os.path.join(HERE, "outputs")) for f in fs]
    names = [n for n in names if n.lower().endswith(EXTENSIONS)]
    return sorted(set(names) | set(also))


def decimals(token):
    """Number of printed decimals of a plain decimal token; None for whole numbers and exponents."""
    if "e" in token.lower() or "." not in token:
        return None
    return len(token.split(".")[1])


def same_number(a, b):
    """'exact', 'tolerance', 'last place' or None, with the relative difference."""
    if a == b:
        return "exact", 0.0
    x, y = float(a), float(b)
    diff, scale = abs(x - y), max(abs(x), abs(y))
    rel = diff / scale if scale else 0.0
    da, db = decimals(a), decimals(b)
    if da is None and db is None and "e" not in (a + b).lower():
        return None, rel                      # whole numbers must match exactly
    if diff <= RTOL * scale + ATOL:
        return "tolerance", rel
    if da is not None and da == db and diff <= 1.000001 * 10.0 ** (-da):
        return "last place", rel
    return None, rel


def compare(name, old, new, report):
    """Compares two versions of one file; fills the report and returns True if reproduced."""
    if old == new:
        report["identical"] += 1
        report["numbers"] += len(NUMBER.findall(old))
        return True
    old_lines, new_lines = old.splitlines(), new.splitlines()
    if len(old_lines) != len(new_lines):
        report["failures"].append(f"{name}: {len(old_lines)} lines stored, {len(new_lines)} regenerated")
        return False
    ok, touched = True, False
    for i, (lo, ln) in enumerate(zip(old_lines, new_lines), 1):
        ta, tb = NUMBER.findall(lo), NUMBER.findall(ln)
        report["numbers"] += len(ta)
        if lo == ln:
            continue
        if NUMBER.split(lo) != NUMBER.split(ln) or len(ta) != len(tb):
            report["failures"].append(f"{name}:{i}: text differs\n    stored:      {lo[:160]}\n    regenerated: {ln[:160]}")
            ok = False
            continue
        for a, b in zip(ta, tb):
            kind, rel = same_number(a, b)
            if kind == "exact":
                continue
            if kind is None:
                report["failures"].append(f"{name}:{i}: {a} stored, {b} regenerated (relative difference {rel:.1e})")
                ok = False
                continue
            touched = True
            report[kind] += 1
            report["max_rel"] = max(report["max_rel"], rel) if kind == "tolerance" else report["max_rel"]
            if kind == "last place":
                report["last_place_examples"].append(f"{name}:{i}: {a} stored, {b} regenerated")
    if ok and touched:
        report["within"] += 1
    return ok


def main():
    ap = argparse.ArgumentParser(description="Rerun the pipeline and check that every stored result is reproduced.")
    ap.add_argument("--no-run", action="store_true", help="do not rerun; compare the current files with the last commit")
    ap.add_argument("--also", action="append", default=[], metavar="FILE", help="also check this result file")
    args = ap.parse_args()

    names = stored_files(args.also)
    if not names:
        sys.exit("No stored result files found in outputs/.")

    stored = {}
    if args.no_run:
        for n in names:
            blob = git("show", "HEAD:" + n)
            if blob is None:
                sys.exit(f"--no-run needs a git checkout with {n} committed.")
            stored[n] = blob.decode("utf-8")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            for n in names:
                dst = os.path.join(tmp, n)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(HERE, n), dst)
            print(f"Stored copies of {len(names)} result files set aside. Running ./run_all.sh ...", flush=True)
            run = subprocess.run(["bash", os.path.join(HERE, "run_all.sh")], cwd=HERE)
            if run.returncode != 0:
                sys.exit(f"FAIL: ./run_all.sh stopped with exit status {run.returncode}.")
            for n in names:
                with open(os.path.join(tmp, n), encoding="utf-8") as f:
                    stored[n] = f.read()

    report = dict(identical=0, within=0, numbers=0, tolerance=0, max_rel=0.0, failures=[],
                  last_place_examples=[], **{"last place": 0})
    failed_files = 0
    for n in names:
        path = os.path.join(HERE, n)
        if not os.path.exists(path):
            report["failures"].append(f"{n}: not produced by the run")
            failed_files += 1
            continue
        with open(path, encoding="utf-8") as f:
            if not compare(n, stored[n], f.read(), report):
                failed_files += 1

    print(f"\nProcessor: {machine()}")
    print(f"Checked {len(names)} result file{'' if len(names) == 1 else 's'}, {report['numbers']:,} numbers.")
    print(f"  identical, character for character: {report['identical']} files")
    if report["within"]:
        print(f"  same values, different last digits: {report['within']} files")
    if report["tolerance"]:
        print(f"    {report['tolerance']:,} numbers differ within tolerance; largest relative difference {report['max_rel']:.1e}")
    if report["last place"]:
        print(f"    {report['last place']:,} rounded numbers differ by one unit in the last printed place:")
        for line in report["last_place_examples"][:10]:
            print("      " + line)
    if report["failures"]:
        print(f"  NOT reproduced: {failed_files} files")
        for line in report["failures"][:40]:
            print("    " + line)
        if len(report["failures"]) > 40:
            print(f"    ... and {len(report['failures']) - 40} more")
        print("\nFAIL: some stored results are not reproduced.")
        sys.exit(1)
    print(f"\nPASS: every stored result is reproduced (relative tolerance {RTOL:g}).")


if __name__ == "__main__":
    main()
