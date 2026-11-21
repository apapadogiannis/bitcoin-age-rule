"""Writes what a program or an AI agent needs to use this package without reading the paper:

    outputs/results.json   gets a "package" header: paper, identifiers, version, licence, citation
    llms.txt               the guide: what the package holds, what it adds, which file to use,
                           what not to use it for

Both are built from CITATION.cff (identity and version), guide.toml (the statements about this
package) and the results themselves, so that no number in them is typed in. Run as the last step
of ./run_all.sh. The script is the same in every replication package; only guide.toml differs.
Standard library only (Python 3.11+).
"""
import csv
import json
import os
import re
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT_DIR", os.path.join(ROOT, "outputs"))
AUTHOR = {"name": "Agisilaos Papadogiannis", "orcid": "https://orcid.org/0009-0002-7753-7052",
          "url": "https://github.com/apapadogiannis"}
CC_BY = "https://creativecommons.org/licenses/by/4.0/"


def citation_file():
    """The plain keys of CITATION.cff: top level, and those of preferred-citation under 'paper.'."""
    top, paper, inside = {}, {}, False
    with open(os.path.join(ROOT, "CITATION.cff"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\s*)([\w-]+):\s*(.*?)\s*$", line)
            if not m or not m.group(3):
                inside = line.startswith("preferred-citation:") or (inside and line.startswith(" "))
                continue
            indent, key, value = len(m.group(1)), m.group(2), m.group(3).strip('"')
            if indent == 0:
                top[key], inside = value, False
            elif inside and indent == 2:
                paper[key] = value
    return top, paper


def numbers(x):
    """How many numbers a result holds."""
    if isinstance(x, bool):
        return 0
    if isinstance(x, (int, float)):
        return 1
    if isinstance(x, dict):
        return sum(numbers(v) for v in x.values())
    if isinstance(x, list):
        return sum(numbers(v) for v in x)
    return 0


def checks(results):
    """For each list of checks in the results: how many claims, and how many agree with the paper."""
    lines = []
    for key, rows in results.items():
        if not key.endswith("_checks"):
            continue
        ok = sum(abs(r["computed"] - r["paper"]) <= r["tolerance"] if "tolerance" in r
                 else str(r["computed"]) == str(r["paper"]) for r in rows)
        how = "within the stated tolerance" if "tolerance" in rows[0] else "exactly"
        lines.append(f"`{key}`: {len(rows):,} figures quoted in the paper, recomputed from the data and compared with the "
                     f"paper's figure; {ok:,} agree {how}. The run fails if any does not.")
    return lines


def cell(h, column):
    """One figure from a stored result table: the row of `file` whose cells equal `row`, column `column`."""
    path = os.path.join(OUT, h["file"])
    with open(path, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if all(r[k] == str(v) for k, v in h["row"].items())]
    if len(rows) != 1:
        raise SystemExit(f"headline '{h['what']}': {len(rows)} rows of {h['file']} match {h['row']}; one is needed")
    value = float(rows[0][column]) * h.get("scale", 1)
    if "decimals" not in h:
        return value
    return int(round(value)) if h["decimals"] == 0 else round(value, h["decimals"])


def tables(g):
    """The stored result tables, with what each holds and the meaning of its columns, checked against the files."""
    out = []
    for t in g.get("table", []):
        with open(os.path.join(OUT, t["file"]), encoding="utf-8", newline="") as f:
            header = next(csv.reader(f))
            n = sum(1 for _ in f)
        unknown = [c for c in t.get("columns", {}) if c not in header]
        missing = [c for c in header if t.get("columns") and c not in t["columns"]]
        if unknown or missing:
            raise SystemExit(f"{t['file']}: columns described but absent {unknown}; present but not described {missing}")
        out.append({"file": "outputs/" + t["file"], "what": t["what"], "rows": n,
                    **({"columns": t["columns"]} if t.get("columns") else {"column_names": header})})
    return out


def headline(results, g):
    """The few figures most often asked for, each taken from a named check or from a cell of a stored
    table, so that none is typed in."""
    out = []
    for h in g.get("headline", []):
        if "file" in h:
            row = {"what": h["what"], "value": cell(h, h["column"]), "unit": h["unit"]}
            if "low_column" in h:
                row["range"] = [cell(h, h["low_column"]), cell(h, h["high_column"])]
                row["range_is"] = h["range_is"]
            out.append({**row, "where": h["where"],
                        "source": {"file": "outputs/" + h["file"], "row": h["row"], "column": h["column"],
                                   **({"multiplied_by": h["scale"]} if "scale" in h else {})}})
            continue
        find = lambda claim: next(r for r in results[h["checks"]] if r["claim"] == claim)
        row = {"what": h["what"], "value": find(h["claim"])["paper"], "unit": h["unit"]}
        if "low" in h:
            row["range"] = [find(h["low"])["paper"], find(h["high"])["paper"]]
            row["range_is"] = h["range_is"]
        if "se" in h:
            row["standard_error"] = find(h["se"])["paper"]
        out.append({**row, "where": h["where"], "check": h["claim"]})
    return out


def wrap(text, width=100, first="", rest=""):
    lines, line = [], first
    for word in text.split():
        if len(line) + len(word) + 1 > width and line.strip():
            lines.append(line.rstrip())
            line = rest
        line += word + " "
    return "\n".join(lines + [line.rstrip()])


def main():
    cff, paper = citation_file()
    with open(os.path.join(ROOT, "guide.toml"), "rb") as f:
        g = tomllib.load(f)
    with open(os.path.join(ROOT, "check_outputs.py"), encoding="utf-8") as f:
        tolerance = re.search(r"RTOL, ATOL = ([\d.e-]+)", f.read()).group(1)

    repo, archive = cff["repository-code"], "https://doi.org/" + cff["doi"]
    title = paper["title"]
    published = "volume" in paper                      # printed, with volume and pages
    forthcoming = "journal" in paper and not published   # accepted, not yet printed
    if forthcoming:
        year = paper.get("year", "forthcoming")
        cite = f"Papadogiannis, A. ({year}). {title}. {paper['journal']}, forthcoming. https://doi.org/{g['ssrn']}"
        article = {"journal": paper["journal"], "status": "forthcoming", **({"year": int(year)} if "year" in paper else {})}
    elif published:
        place = str(paper["volume"]) + (f"({paper['issue']})" if "issue" in paper else "")
        pages = f"{paper['start']}-{paper['end']}" if "end" in paper else str(paper["start"])
        link = paper.get("url") or "https://doi.org/" + paper["doi"]
        cite = f"Papadogiannis, A. ({paper['year']}). {title}. {paper['journal']}, {place}, {pages}. {link}"
        article = {"journal": paper["journal"], "volume": int(paper["volume"]),
                   **({"issue": int(paper["issue"])} if "issue" in paper else {}),
                   ("pages" if "end" in paper else "article_number"): pages, "year": int(paper["year"]), "doi": link}
    else:
        cite = f"Papadogiannis, A. ({paper['year']}). {title}. Working paper. https://doi.org/{g['ssrn']}"
        article = None
    cite_package = (f"Papadogiannis, A. ({cff['date-released'][:4]}). {title}. Replication package, version "
                    f"{cff['version']}. Zenodo. {archive}")

    header = {
        "title": title, "author": AUTHOR,
        "status": "published article" if published else "forthcoming article" if forthcoming else "working paper",
        **({"article": article} if article else {}),
        "preprint": "https://doi.org/" + g["ssrn"],
        "repository": repo, "archive": archive, "version": cff["version"], "released": cff["date-released"],
        "data_as_of": g["data_as_of"], "units": g["units"],
        "licence": {"results": "CC-BY-4.0", "url": CC_BY,
                    "condition": "Reuse of the results is allowed with credit to the paper.",
                    "code": "MIT", "third_party_data": g["third_party"]},
        "cite_as": cite, "cite_package": cite_package, "describe_as": g["describe_as"],
        "guide": "llms.txt",
        **({"fields": g["fields"]} if g.get("fields") else {}),     # what each key of the results means
    }
    path = os.path.join(OUT, "results.json")
    results = {}
    if not g.get("table"):        # a package whose results are tables builds the file from them each time
        with open(path, encoding="utf-8") as f:
            results = json.load(f)
    results.pop("package", None)
    results.pop("headline", None)
    results.pop("glossary", None)
    listed = tables(g)
    if listed:
        results["tables"] = listed
    n_checks = sum(len(v) for k, v in results.items() if k.endswith("_checks"))
    count = (f"{n_checks:,} checks" if n_checks else f"a description of {len(listed)} result tables" if listed
             else f"{numbers(results):,} numbers")
    top = headline(results, g)
    if top:
        results = {"headline": top, **results}
    glossary = g.get("glossary", {})
    if glossary:
        results = {**{k: results[k] for k in ("headline",) if k in results}, "glossary": glossary,
                   **{k: v for k, v in results.items() if k != "headline"}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"package": header, **results}, f, indent=2, ensure_ascii=False)
        f.write("\n")

    item = lambda t: wrap(t, first="- ", rest="  ")
    step = lambda i, t: wrap(t, first=f"{i}. ", rest="   ")
    status = (f"Published in {paper['journal']}, {place}, {paper['year']}, {'pp. ' if 'end' in paper else 'article '}{pages}: {link}"
              if published else
              f"Forthcoming in {paper['journal']}{' (' + paper['year'] + ')' if 'year' in paper else ''}. "
              f"Preprint: https://doi.org/{g['ssrn']}"
              if forthcoming else f"Working paper: https://doi.org/{g['ssrn']}")
    adds = list(g["adds"]) + checks(results) + [
        f"The results are stored as they were when the paper's numbers were taken from them. A check "
        f"reruns the code on the stored data and compares every stored result file with the fresh one, "
        f"number by number (relative tolerance {tolerance}; text and whole numbers exactly). It runs on "
        f"every change and once a month, and the badge in the README shows the last run."]
    live = g.get("live_tool")
    not_for = list(g["not_for"]) + ([f"Current figures. Use the live tool: {live['name']}, {live['url']} ({live['what']})"] if live else [])
    files = [f"outputs/results.json: {g['results_file']} It holds {count}, and under `package` the paper, the "
             f"identifiers, the version, the licence and the citation."
             + (" Start with its `headline` list, which is repeated below." if top else " Start here.")] + list(g["files"])
    raw = repo.replace("https://github.com/", "https://raw.githubusercontent.com/") + "/main/"

    def line(h):
        text = f"{h['what']}: {h['value']} {h['unit']}"
        if "range" in h:
            text += f" ({h['range_is']} {h['range'][0]} to {h['range'][1]})"
        if "standard_error" in h:
            text += f" (standard error {h['standard_error']})"
        return item(f"{text}. {h['where']}.")

    guide = "\n".join([
        f"# {title}", "",
        wrap(g["what"], first="> ", rest="> "), "",
        f"Replication package by {AUTHOR['name']} ({AUTHOR['url']}).",
        status,
        f"Code and data: {repo}  Archive: {archive}",
        f"Version {cff['version']}, released {cff['date-released']}. A package is a fixed record: it changes only by a new",
        "release, and a release that changes a reported number gets a new major version.",
        "This file is written for AI agents and other programs. People should start at the README.", "",
        "## Coverage", "", *[item(t) for t in g["coverage"]], "",
        *(["## Headline figures", "",
           ("Each is read from one cell of a stored result table, named in outputs/results.json."
            if listed else "As printed in the paper. Each is one of the checks in outputs/results.json."), "",
           *[line(h) for h in top], ""] if top else []),
        "## What this adds over reading the paper or recomputing", "",
        *[step(i, t) for i, t in enumerate(adds, 1)], "",
        *(["## Labels of the checks", "",
           "The checks keep the audit script's short labels. What the recurring words and prefixes mean:", "",
           *[item(f"{k}: {v}") for k, v in glossary.items()], ""] if glossary else []),
        *(["## Fields of outputs/results.json", "", *[item(f"`{k}`: {v}") for k, v in g["fields"].items()], ""]
          if g.get("fields") else []),
        *(["## Result tables", "", "One CSV file each in outputs/. The columns of each are described in outputs/results.json, under `tables`.", "",
           *[item(f"{t['file']} ({t['rows']} rows): {t['what']}") for t in listed], ""] if listed else []),
        "## Files", "", *[item(t) for t in files], "",
        f"Raw files: {raw}<path>, for example {raw}outputs/results.json", "",
        "## How to read the figures", "", *[item(t) for t in g["read"]], "",
        "## Do not use this for", "", *[item(t) for t in not_for], "",
        "## Source, licence and credit", "",
        wrap(f"The results in outputs/ are released under CC BY 4.0 ({CC_BY}). The licence allows any reuse and "
             "has one condition: credit. If you use a figure from this package in an answer, a report or a data "
             "set, cite the paper. The code is under the MIT License."), "",
        wrap(g["third_party"]), "",
        f"Cite as: {cite}", "",
        f"The package itself: {cite_package}", "",
        wrap(f"To describe the source in a sentence: {g['describe_as']}"), "",
        "The same licence and citation are inside outputs/results.json, under `package`.", ""])
    with open(os.path.join(ROOT, "llms.txt"), "w", encoding="utf-8") as f:
        f.write(guide)
    print(f"results.json: header written, {count}. llms.txt written.")


if __name__ == "__main__":
    main()
