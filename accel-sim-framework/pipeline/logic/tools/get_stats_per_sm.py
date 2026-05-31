#!/usr/bin/env python3
"""Extract per-SM GCStack CPI stack metrics from accel-sim .o output files."""

import argparse
import csv
import glob
import os
import re
import sys

GCSTACK_FIELDS = [
    'gcstack_base', 'gcstack_idle', 'gcstack_finished', 'gcstack_empty_ibuf',
    'gcstack_last_ins', 'gcstack_sync', 'gcstack_control', 'gcstack_mem_data',
    'gcstack_com_data', 'gcstack_mem_struct', 'gcstack_com_struct', 'gcstack_tot',
]

CSV_FIELDNAMES = ['config', 'trace', 'kernel_name', 'kernel_uid', 'sm_id'] + GCSTACK_FIELDS + ['gcstack_cpi']

_SHADER_CORE_RE   = re.compile(r'^SHADER_CORE__ID(\d+)\s*$')
_GCSTACK_FIELD_RE = re.compile(r'^(gcstack_\w+)\s*=\s*([\d.]+)')
_KERNEL_NAME_RE   = re.compile(r'^kernel_name\s*=\s*(.+)$')
_KERNEL_UID_RE    = re.compile(r'^kernel_launch_uid\s*=\s*(\d+)$')
_GCSTACK_HDR_RE   = re.compile(r'^={5,}.*GCStack CPI Stack Metrics.*={5,}')
_SECTION_END_RE   = re.compile(r'^={20,}\s*$')  # pure === separator line, no text


def _fmt(v: float) -> str:
    return f"{v:.4f}"


def _make_row(config, trace, kernel_name, kernel_uid, sm_id, fields: dict) -> dict:
    base = fields.get('gcstack_base', 0.0)
    tot  = fields.get('gcstack_tot',  0.0)
    cpi  = _fmt(tot / base) if base != 0.0 else ''
    row = {
        'config':      config,
        'trace':       trace,
        'kernel_name': kernel_name,
        'kernel_uid':  kernel_uid if kernel_uid is not None else '',
        'sm_id':       sm_id,
        'gcstack_cpi': cpi,
    }
    for f in GCSTACK_FIELDS:
        row[f] = _fmt(fields.get(f, 0.0))
    return row


def _parse_o_file(path: str, config: str, trace: str) -> list:
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        lines = fh.readlines()

    rows = []
    n = len(lines)
    i = 0
    kernel_name = None
    kernel_uid  = None

    while i < n:
        stripped = lines[i].strip()

        m = _KERNEL_NAME_RE.match(stripped)
        if m:
            kernel_name = m.group(1).strip()
            i += 1
            continue

        m = _KERNEL_UID_RE.match(stripped)
        if m:
            kernel_uid = int(m.group(1))
            i += 1
            continue

        if _GCSTACK_HDR_RE.match(stripped):
            i += 1
            sm_data = {}

            while i < n:
                inner = lines[i].strip()

                if _SECTION_END_RE.match(inner):
                    i += 1
                    break

                m = _SHADER_CORE_RE.match(inner)
                if m:
                    sm_id = int(m.group(1))
                    sm_fields = {}
                    i += 1
                    while i < n:
                        field_line = lines[i].strip()
                        if _SHADER_CORE_RE.match(field_line) or _SECTION_END_RE.match(field_line):
                            break
                        fm = _GCSTACK_FIELD_RE.match(field_line)
                        if fm and fm.group(1) in set(GCSTACK_FIELDS):
                            sm_fields[fm.group(1)] = float(fm.group(2))
                        i += 1
                    sm_data[sm_id] = sm_fields
                    continue

                i += 1

            if kernel_name is not None and sm_data:
                for sm_id in sorted(sm_data.keys()):
                    rows.append(_make_row(config, trace, kernel_name, kernel_uid, sm_id, sm_data[sm_id]))
                sum_fields = {f: sum(sm.get(f, 0.0) for sm in sm_data.values()) for f in GCSTACK_FIELDS}
                rows.append(_make_row(config, trace, kernel_name, kernel_uid, 'SUM', sum_fields))

            continue

        i += 1

    return rows


def main():
    parser = argparse.ArgumentParser(
        description='Extract per-SM GCStack CPI metrics from accel-sim .o simulation logs.'
    )
    parser.add_argument('-r', '--run_dir',       required=True,
                        help='Root output dir: {run_dir}/{benchmark}/*/{config}/{run_id}.o')
    parser.add_argument('-B', '--benchmark_list', required=True,
                        help='Comma-separated benchmark names')
    parser.add_argument('-C', '--configs_list',   required=True,
                        help='Comma-separated config names')
    parser.add_argument('-d', '--run_id',         required=True,
                        help='Run ID / date string, e.g. 2026_05_19__23_11')
    args = parser.parse_args()

    benchmarks = [b.strip() for b in args.benchmark_list.split(',')]
    configs    = [c.strip() for c in args.configs_list.split(',')]
    run_id     = args.run_id.strip()

    writer = csv.DictWriter(sys.stdout, fieldnames=CSV_FIELDNAMES, lineterminator='\n')
    writer.writeheader()

    for benchmark in benchmarks:
        # benchmark may be "Suite:dirname" (e.g. "4K-UHD:render_passes") — use dirname for path
        bench_dir = benchmark.split(':', 1)[-1]
        for config in configs:
            pattern = os.path.join(args.run_dir, bench_dir, '*', config, f'{run_id}.o')
            matches = sorted(glob.glob(pattern))
            if not matches:
                print(f"WARNING: no .o file for {bench_dir}/{config}/{run_id}", file=sys.stderr)
                continue
            for o_path in matches:
                for row in _parse_o_file(o_path, config, bench_dir):
                    writer.writerow(row)


if __name__ == '__main__':
    main()
