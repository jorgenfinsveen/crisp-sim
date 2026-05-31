#!/usr/bin/env python3
"""Extract per-memory-partition metrics from accel-sim .o output files."""

import argparse
import csv
import glob
import os
import re
import sys

CSV_FIELDNAMES = [
    'config', 'trace', 'kernel_name', 'kernel_uid',
    'partition_id', 'sub_partition_id', 'global_sub_partition_id',
    'DRAM_bandwidth', 'L2_bandwidth', 'total_responses', 'response_parallism',
    'total_requests', 'request_parallism', 'n_kernel_cycle',
]

_MEM_PART_HDR_RE = re.compile(r'^={5,}.*Memory Partition Activity.*={5,}')
_SECTION_END_RE  = re.compile(r'^={20,}\s*$')
_MEM_PART_ID_RE  = re.compile(r'^Memory_Partition_(\d+)\s*$')
_SUB_PART_ID_RE  = re.compile(r'^Sub_Partition_(\d+)\s*$')
_TOTAL_RE        = re.compile(r'^Total kernel results\s*$')
_KERNEL_NAME_RE  = re.compile(r'^kernel_name\s*=\s*(.+)$')
_KERNEL_UID_RE   = re.compile(r'^kernel_launch_uid\s*=\s*(\d+)$')
_FIELD_RE        = re.compile(r'^([\w_]+)\s*=\s*([\d.]+)')


def _fmt(v: float) -> str:
    return f"{v:.4f}"


def _sub_row(config, trace, kernel_name, kernel_uid,
             partition_id, sub_local_id, global_sub_id, sub_fields, n_cycle):
    return {
        'config':                config,
        'trace':                 trace,
        'kernel_name':           kernel_name,
        'kernel_uid':            kernel_uid if kernel_uid is not None else '',
        'partition_id':          partition_id,
        'sub_partition_id':      sub_local_id,
        'global_sub_partition_id': global_sub_id if global_sub_id is not None else '',
        'DRAM_bandwidth':        _fmt(sub_fields.get('DRAM_bandwidth_sub_partition',  0.0)),
        'L2_bandwidth':          _fmt(sub_fields.get('L2_bandwidth_sub_partition',    0.0)),
        'total_responses':       _fmt(sub_fields.get('total_responses_sub_partition', 0.0)),
        'response_parallism':    _fmt(sub_fields.get('response_parallism_sub_partition', 0.0)),
        'total_requests':        _fmt(sub_fields.get('total_requests_sub_partition',  0.0)),
        'request_parallism':     _fmt(sub_fields.get('request_parallism_sub_partition', 0.0)),
        'n_kernel_cycle':        str(int(n_cycle)) if n_cycle is not None else '',
    }


def _total_row(config, trace, kernel_name, kernel_uid, total_fields):
    return {
        'config':                config,
        'trace':                 trace,
        'kernel_name':           kernel_name,
        'kernel_uid':            kernel_uid if kernel_uid is not None else '',
        'partition_id':          'TOTAL',
        'sub_partition_id':      '',
        'global_sub_partition_id': '',
        'DRAM_bandwidth':        _fmt(total_fields.get('DRAM_bandwidth',     0.0)),
        'L2_bandwidth':          _fmt(total_fields.get('L2_bandwidth',       0.0)),
        'total_responses':       _fmt(total_fields.get('total_responses',    0.0)),
        'response_parallism':    _fmt(total_fields.get('response_parallism', 0.0)),
        'total_requests':        _fmt(total_fields.get('total_requests',     0.0)),
        'request_parallism':     _fmt(total_fields.get('request_parallism',  0.0)),
        'n_kernel_cycle':        '',
    }


def _flush_sub(rows, config, trace, kernel_name, kernel_uid,
               partition_id, sub_local_id, global_sub_id, sub_fields, n_cycle):
    if sub_local_id is not None:
        rows.append(_sub_row(config, trace, kernel_name, kernel_uid,
                             partition_id, sub_local_id, global_sub_id, sub_fields, n_cycle))


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

        if not _MEM_PART_HDR_RE.match(stripped):
            i += 1
            continue

        # ── entered Memory Partition Activity section ──
        i += 1
        partition_id      = None
        part_fields       = {}   # partition-level fields (incl. n_kernel_cycle)
        sub_local_id      = None
        sub_global_id     = None
        sub_fields        = {}
        in_total          = False
        total_fields      = {}
        sub_rows_buf      = []   # collect sub-partition rows; emit alongside TOTAL

        while i < n:
            stripped = lines[i].strip()

            # section end
            if _SECTION_END_RE.match(stripped):
                _flush_sub(sub_rows_buf, config, trace, kernel_name, kernel_uid,
                           partition_id, sub_local_id, sub_global_id,
                           sub_fields, part_fields.get('n_kernel_cycle'))
                rows.extend(sub_rows_buf)
                if total_fields:
                    rows.append(_total_row(config, trace, kernel_name, kernel_uid, total_fields))
                i += 1
                break

            # Total kernel results block
            if _TOTAL_RE.match(stripped):
                _flush_sub(sub_rows_buf, config, trace, kernel_name, kernel_uid,
                           partition_id, sub_local_id, sub_global_id,
                           sub_fields, part_fields.get('n_kernel_cycle'))
                sub_local_id = None
                sub_fields   = {}
                sub_global_id = None
                in_total     = True
                partition_id = None
                i += 1
                continue

            # new memory partition
            m = _MEM_PART_ID_RE.match(stripped)
            if m:
                _flush_sub(sub_rows_buf, config, trace, kernel_name, kernel_uid,
                           partition_id, sub_local_id, sub_global_id,
                           sub_fields, part_fields.get('n_kernel_cycle'))
                partition_id  = int(m.group(1))
                part_fields   = {}
                sub_local_id  = None
                sub_fields    = {}
                sub_global_id = None
                i += 1
                continue

            # new sub-partition (header is indented; match against stripped)
            m = _SUB_PART_ID_RE.match(stripped)
            if m:
                _flush_sub(sub_rows_buf, config, trace, kernel_name, kernel_uid,
                           partition_id, sub_local_id, sub_global_id,
                           sub_fields, part_fields.get('n_kernel_cycle'))
                sub_local_id  = int(m.group(1))
                sub_fields    = {}
                sub_global_id = None
                i += 1
                continue

            # field value line
            fm = _FIELD_RE.match(stripped)
            if fm:
                name = fm.group(1)
                val  = float(fm.group(2))
                if in_total:
                    total_fields[name] = val
                elif sub_local_id is not None:
                    if name == 'global_sub_partition_id':
                        sub_global_id = int(val)
                    else:
                        sub_fields[name] = val
                elif partition_id is not None:
                    part_fields[name] = val

            i += 1

        continue  # back to outer loop (i already advanced)

    return rows


def main():
    parser = argparse.ArgumentParser(
        description='Extract per-memory-partition metrics from accel-sim .o simulation logs.'
    )
    parser.add_argument('-r', '--run_dir',        required=True,
                        help='Root output dir: {run_dir}/{benchmark}/*/{config}/{run_id}.o')
    parser.add_argument('-B', '--benchmark_list',  required=True,
                        help='Comma-separated benchmark names')
    parser.add_argument('-C', '--configs_list',    required=True,
                        help='Comma-separated config names')
    parser.add_argument('-d', '--run_id',          required=True,
                        help='Run ID / date string, e.g. 2026_05_29__13_25')
    args = parser.parse_args()

    benchmarks = [b.strip() for b in args.benchmark_list.split(',')]
    configs    = [c.strip() for c in args.configs_list.split(',')]
    run_id     = args.run_id.strip()

    writer = csv.DictWriter(sys.stdout, fieldnames=CSV_FIELDNAMES, lineterminator='\n')
    writer.writeheader()

    for benchmark in benchmarks:
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
