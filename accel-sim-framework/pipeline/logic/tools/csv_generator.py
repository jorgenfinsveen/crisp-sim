#!/usr/bin/env python3
import os
import re
import sys
import csv
import glob
import parser
from pathlib import Path
from collections import defaultdict, OrderedDict

DIR_PATH: Path = Path(__file__).resolve().parent
PIPELINE_ROOT: Path = DIR_PATH.parent
PIPELINE_CONFIG_FILE: Path = os.path.join(PIPELINE_ROOT, "setup", "pipeline.yaml")

DASH_RE = re.compile(r"^-{5,}\s*,*")
CONFIG_LINE_RE = re.compile(r"^(?P<gpu>[^;]+);;(?P<kv>[^=]+)=(?P<val>.+)$")

# PARSER: Path = os.path.join(DIR_PATH, "parser.py")
# spec = importlib.util.spec_from_file_location("parser", PARSER)
# parser = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(parser)

pipeline = {}
experiment = {}

def parse_pipeline_config():
    global pipeline
    pipeline = parser.get_pipeline(PIPELINE_CONFIG_FILE)

def parse_experiment():
    global experiment
    experiment = parser.get_experiment(pipeline.experiment.name, pipeline.experiment.path)
    experiment.results_dir = Path(os.path.expandvars(experiment.results_dir))
    experiment.logfiles = Path(os.path.expandvars(experiment.logfiles))


def pick_existing_glob(*patterns: str) -> str:
    hits = []
    for pat in patterns:
        hits.extend(glob.glob(pat))
    hits = sorted(set([h for h in hits if os.path.isfile(h)]))
    if hits:
        return hits[0]
    tried = "\n  - " + "\n  - ".join(patterns)
    raise FileNotFoundError(f"Could not find required file. Tried:{tried}")


def pick_existing_dir(*candidates: str) -> str:
    for p in candidates:
        if p and os.path.isdir(p):
            return p
    tried = "\n  - " + "\n  - ".join([c for c in candidates if c])
    raise FileNotFoundError(f"Could not find required directory. Tried:{tried}")



def find_matching_runs(path: Path, experiment_name: str):
    sim_logs = parser.get_simulator_logs(path)
    matches = []
    for key, log in sim_logs.items():
        if log.experiment != experiment_name:
            continue
        date = key[4:] if key.startswith('sim-') else key
        matches.append((key, date, log.configs))
    matches.sort(key=lambda x: x[1])
    return matches


def parse_configs_for_run(configs_list):
    out = {}
    for item in configs_list:
        m = CONFIG_LINE_RE.match(str(item).strip())
        if not m:
            continue
        gpu = m.group("gpu").strip()
        param = m.group("kv").strip()
        val = m.group("val").strip()
        out[gpu] = (param, val)
    return out


def find_total_csv_for_date(total_dir: str, date_key: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(total_dir, f"*{date_key}*")))
    hits = [h for h in hits if h.lower().endswith(".csv")]
    if not hits:
        return None
    return hits[-1]


def safe_float(x: str):
    x = (x or "").strip()
    if not x or x.upper() == "NA":
        return None
    try:
        return float(x)
    except ValueError:
        return None


def group_columns(header_cols):
    # Todo: Legg på et frivillig parameter som velger om man skal slå sammen kernels innenfor en benchmark eller ikke.
    # Todo: Parameteret kan være basert på hvorvidt CPI er mål-resultatet.
    # Todo: Hvis nei: I steden for å appende idx, append et tuppel, sub, hvor i0 er group (uten split),
    # Todo: ... og i1 er indeksen for den ene kernelen. Legg til ny entry i groups hvor key er group (med split) og
    # Todo: ... val er en liste med alle sub-tuppeler.
    # Todo: Etter dette er gjort må main justeres for å sjekke hvorvidt det frivillige parameteret var satt, og i såfall
    # Todo: ... ta høyde for at det skal opereres med et dict som inneholder en liste med tupler.
    # Todo: Alle grupper med et navn som starter på den samme frasen kan slås sammen slik at vi ender opp med én samlet
    # Todo: ... verdi for hver av de 5 forskjellige trace-pakkene.
    # Todo: Til slutt må bar-chart oppdateres slik at den slår sammen alle fra samme app, men gir de forskjellig farger
    # Todo: ... i søylediagrammet.
    groups = OrderedDict()
    for idx, col in enumerate(header_cols):
        group = col.split("--", 1)[0].strip()
        groups.setdefault(group, []).append(idx)
    return groups


def avg_of_indices(vals, indices):
    nums = []
    for i in indices:
        if i >= len(vals):
            continue
        v = safe_float(vals[i])
        if v is not None:
            nums.append(v)
    if not nums:
        return None
    return sum(nums) / len(nums)


def parse_metric_block(csv_path: str, metric: str):
    metric_line_re = re.compile(rf"^\s*{re.escape(metric)}\b")
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()

    n = len(lines)
    for i in range(n):
        if not metric_line_re.search(lines[i]):
            continue

        k = i + 1
        while k < n and not lines[k].startswith("CFG,"):
            if DASH_RE.match(lines[k].strip()):
                break
            k += 1

        if k >= n or not lines[k].startswith("CFG,"):
            continue

        header = next(csv.reader([lines[k].strip()]))
        header_cols = header[1:]
        rows = {}

        j = k + 1
        while j < n:
            l = lines[j].strip()
            if not l:
                j += 1
                continue
            if DASH_RE.match(l):
                break
            rec = next(csv.reader([l]))
            if not rec:
                j += 1
                continue
            cfg = rec[0].strip()
            vals = rec[1:]
            if len(vals) < len(header_cols):
                vals += [""] * (len(header_cols) - len(vals))
            elif len(vals) > len(header_cols):
                vals = vals[: len(header_cols)]
            rows[cfg] = vals
            j += 1

        return header_cols, rows

    raise RuntimeError(f"Could not find metric block '{metric}' in {csv_path}")


def fmt(x):
    if x is None:
        return ""
    return f"{x:.4f}"


def main():
    global pipeline
    parse_pipeline_config()
    parse_experiment()

    metric = pipeline.collect.metric
    sim_logs_path = os.path.join(experiment.results_dir, 'output', 'simulator_logs.yaml')

    export_dir = os.path.join(experiment.results_dir, 'export')
    export_total_dir = os.path.join(export_dir, 'total')

    runs = find_matching_runs(sim_logs_path, experiment.name)
    if not runs:
        print(f"No runs matched experiment.name={experiment.name}", file=sys.stderr)
        sys.exit(2)

    per_gpu_rows = defaultdict(list)
    all_group_keys = OrderedDict()

    for _, date_key, configs_list in runs:
        total_csv = find_total_csv_for_date(export_total_dir, date_key)
        if not total_csv:
            print(f"WARNING: No total CSV found for date {date_key} in {export_total_dir}", file=sys.stderr)
            continue

        cfg_param_map = parse_configs_for_run(configs_list)
        header_cols, rows = parse_metric_block(total_csv, metric)
        groups = group_columns(header_cols)

        groups_no_avg = OrderedDict((g, idxs) for g, idxs in groups.items() if g != "AVG")
        for g in groups_no_avg:
            all_group_keys.setdefault(g, None)

        for gpu_name, vals in rows.items():
            if gpu_name not in cfg_param_map:
                continue

            param_name, param_val = cfg_param_map[gpu_name]
            out_row = {param_name: param_val}

            group_avgs = []
            for g, idxs in groups_no_avg.items():
                a = avg_of_indices(vals, idxs)
                out_row[g] = fmt(a)
                if a is not None:
                    group_avgs.append(a)

            out_row["AVG"] = fmt(sum(group_avgs) / len(group_avgs)) if group_avgs else ""
            per_gpu_rows[gpu_name].append((param_name, out_row))

    if not per_gpu_rows:
        print("No rows produced. Do the CFG names in CSV match simulator_logs configs GPU names?", file=sys.stderr)
        sys.exit(3)



    for gpu, row_pairs in per_gpu_rows.items():
        gpu = gpu.split('_')[0]
        out_gpu_dir = os.path.join(export_dir, gpu)
        os.makedirs(out_gpu_dir, exist_ok=True)
        out_path = os.path.join(out_gpu_dir, f"{metric}.csv")

        param_names = [p for (p, _) in row_pairs]
        param_name = max(set(param_names), key=param_names.count)

        fieldnames = [param_name] + list(all_group_keys.keys()) + ["AVG"]

        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for _, r in row_pairs:
                if param_name not in r:
                    r[param_name] = ""
                w.writerow({k: r.get(k, "") for k in fieldnames})

        print(f"Wrote {out_path} ({len(row_pairs)} rows)")

    print(f"Done. Experiment={experiment.name}, metric={metric}")


if __name__ == "__main__":
    main()
