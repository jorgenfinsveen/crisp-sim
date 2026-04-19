#!/usr/bin/env python3
import os
import re
import sys
import csv
import glob
import parser
import yaml
from pathlib import Path
from collections import defaultdict, OrderedDict

DIR_PATH: Path = Path(__file__).resolve().parent
PIPELINE_ROOT: Path = DIR_PATH.parent
PIPELINE_CONFIG_FILE: Path = os.path.join(PIPELINE_ROOT, "setup", "pipeline.yaml")

DASH_RE = re.compile(r"^-{5,}\s*,*")
CONFIG_LINE_RE = re.compile(r"^(?P<gpu>[^;]+);;(?P<kv>[^=]+)=(?P<val>.+)$")
KERNEL_ID_SUFFIX_RE = re.compile(r"-\d+$")

pipeline = {}

def find_matching_runs(path: Path, experiment_name: str):
    sim_logs = parser.get_simulator_logs(path)
    matches = []
    for key, log in sim_logs.items():
        if log.experiment != experiment_name:
            continue
        date = key[4:] if key.startswith("sim-") else key
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

def base_gpu_name(name: str) -> str:
    return name.split("_", 1)[0].strip()

def safe_float(x: str):
    x = (x or "").strip()
    if not x or x.upper() == "NA":
        return None
    try:
        return float(x)
    except ValueError:
        return None

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

def trace_from_col(col: str) -> str:
    return col.split("--", 1)[0].strip() if "--" in col else col.strip()

def kernel_base_from_col(col: str) -> str:
    after = col.split("--", 1)[1].strip() if "--" in col else col.strip()
    return KERNEL_ID_SUFFIX_RE.sub("", after)

def mesa_family(kernel_base: str) -> str:
    if kernel_base.startswith("MESA_SHADER_VERTEX"):
        return "MESA_SHADER_VERTEX"
    if kernel_base.startswith("MESA_SHADER_FRAGMENT"):
        return "MESA_SHADER_FRAGMENT"
    if kernel_base.startswith("MESA_SHADER"):
        parts = kernel_base.split("_")
        return "_".join(parts[:3]) if len(parts) >= 3 else "MESA_SHADER"
    return "MESA_OTHER"

def zn2_family(kernel_base: str) -> str:
    if "__" in kernel_base:
        tail = kernel_base.rsplit("__", 1)[-1]
        tail = tail.split("N__", 1)[-1]
        if tail:
            return f"ZN2__{tail}"
    if "_" in kernel_base:
        suf = kernel_base.rsplit("_", 1)[-1]
        if suf and len(suf) <= 32:
            return f"ZN2_{suf}"
    return "ZN2_OTHER"

def kernel_family_from_base(kernel_base: str) -> str:
    if kernel_base.startswith("MESA_SHADER"):
        return mesa_family(kernel_base)
    if kernel_base.startswith("_ZN2nv"):
        return zn2_family(kernel_base)
    if kernel_base.startswith("_Z"):
        return "Z_OTHER"
    return "OTHER"

def group_trace_kernel_families(header_cols):
    groups = OrderedDict()
    for idx, col in enumerate(header_cols):
        if col.strip() == "AVG":
            continue
        t = trace_from_col(col)
        kb = kernel_base_from_col(col)
        fam = kernel_family_from_base(kb)
        key = f"{t}/{fam}"
        groups.setdefault(key, []).append(idx)
    return groups

def find_total_csv_for_date(total_dir: str, date_key: str) -> str | None:
    hits = sorted(glob.glob(os.path.join(total_dir, f"*{date_key}*")))
    hits = [h for h in hits if h.lower().endswith(".csv")]
    if not hits:
        return None
    return hits[-1]

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

def load_experiment_cfg(pipeline_obj):
    exp_name = pipeline_obj.experiment.name
    exp_file = os.path.expandvars(pipeline_obj.experiment.path)
    with open(exp_file, "r", encoding="utf-8") as f:
        all_exps = yaml.safe_load(f) or {}
    if exp_name not in all_exps:
        raise KeyError(f"Experiment '{exp_name}' not found in {exp_file}. Available: {', '.join(all_exps.keys())}")
    return all_exps[exp_name], exp_name

def main():
    global pipeline
    pipeline = parser.get_pipeline(PIPELINE_CONFIG_FILE)

    exp_cfg, exp_name = load_experiment_cfg(pipeline)
    metric = pipeline.collect.metric

    results_dir = os.path.expandvars(exp_cfg["results_dir"])
    sim_logs_path = os.path.join(results_dir, "output", "simulator_logs.yaml")

    export_dir = os.path.join(results_dir, "export")
    export_total_dir = os.path.join(export_dir, "total")

    runs = find_matching_runs(sim_logs_path, exp_name)
    if not runs:
        sys.exit(2)

    per_gpu_rows = defaultdict(list)
    all_group_keys = OrderedDict()

    for _, date_key, configs_list in runs:
        total_csv = find_total_csv_for_date(export_total_dir, date_key)
        if not total_csv:
            continue

        cfg_param_map = parse_configs_for_run(configs_list)
        header_cols, rows = parse_metric_block(total_csv, metric)
        groups_no_avg = group_trace_kernel_families(header_cols)

        for g in groups_no_avg:
            all_group_keys.setdefault(g, None)

        for cfg_name, vals in rows.items():
            base_gpu = base_gpu_name(cfg_name)

            param_pair = cfg_param_map.get(cfg_name) or cfg_param_map.get(base_gpu)
            if not param_pair:
                continue

            param_name, param_val = param_pair
            out_row = {param_name: param_val}

            bucket_vals = []
            for g, idxs in groups_no_avg.items():
                a = avg_of_indices(vals, idxs)
                out_row[g] = fmt(a)
                if a is not None:
                    bucket_vals.append(a)

            out_row["AVG"] = fmt(sum(bucket_vals) / len(bucket_vals)) if bucket_vals else ""
            per_gpu_rows[base_gpu].append((param_name, out_row))

    if not per_gpu_rows:
        sys.exit(3)

    for gpu, row_pairs in per_gpu_rows.items():
        out_gpu_dir = os.path.join(export_dir, gpu)
        os.makedirs(out_gpu_dir, exist_ok=True)
        out_path = os.path.join(out_gpu_dir, f"{exp_name}.csv")

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

    print(f"Done. Experiment={exp_name}, metric={metric}")

if __name__ == "__main__":
    main()
