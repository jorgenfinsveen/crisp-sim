#!/usr/bin/env python3

import os
import yaml
import argparse
from pathlib import Path
import parser as ps
from datetime import datetime
from model.simlog import SimulatorLogs, SimulatorLog
from model.namespace import NS

IGNORE_DIRS = ['.post-sim', 'gpgpu-sim-builds']

argparser = argparse.ArgumentParser()
argparser.add_argument("--exp",      required=True, help="Name of the experiment.")
argparser.add_argument("--date_1",   required=True, help="First date to merge. [YYYY_mm_DD__HH_MM].")
argparser.add_argument("--date_2",   required=True, help="Second date to merge. [YYYY_mm_DD__HH_MM].")
argparser.add_argument("--new_date", required=False, help="New date. [YYYY_mm_DD__HH_MM].")
argparser.add_argument("--dir",      required=True, help="Target results-dir e.g., '$ACCEL_SIM/pipeline/results'.")
args = argparser.parse_args()


experiment_name = args.exp.strip()
date_1 = args.date_1.strip()
date_2 = args.date_2.strip()
new_date = args.new_date.strip() if args.new_date else date_1

experiment_dir: Path = Path(os.path.join(args.dir, 'output', args.exp))
sim_logs_path:  Path = Path(os.path.join(args.dir, 'output', 'simulator_logs.yaml'))
logfiles_path:   Path = Path(os.path.join(args.dir, 'logfiles'))


def get_path(path, *paths) -> Path:
    p = path
    for arg in paths:
        p = os.path.join(p, arg)
    p = Path(os.path.expandvars(p))

    if not os.path.exists(p):
        raise FileNotFoundError(f'File not found: {p}')
    return p

def get_benchmarks_from_both(sim_logs: SimulatorLogs) -> list:
    entry_1 = SimulatorLog(sim_logs[f'sim-{date_1}'])
    entry_2 = SimulatorLog(sim_logs[f'sim-{date_2}'])

    benchmarks: list = entry_1.benchmarks + entry_2.benchmarks

    return list(dict.fromkeys(benchmarks))

def get_benchmarks(sim_logs: SimulatorLogs) -> list:
    entry = SimulatorLog(sim_logs[f'sim-{new_date}'])
    return list(dict.fromkeys(entry.benchmarks))

def get_configs(sim_logs: SimulatorLogs) -> list:
    entry_1 = SimulatorLog(sim_logs[f'sim-{date_1}'])
    entry_2 = SimulatorLog(sim_logs[f'sim-{date_2}'])

    configs: list = entry_1.configs + entry_2.configs

    return list(dict.fromkeys(configs))

def get_sim_log_results(sim_logs: SimulatorLogs):
    entry_1 = SimulatorLog(sim_logs[f'sim-{date_1}'])
    entry_2 = SimulatorLog(sim_logs[f'sim-{date_2}'])

    return dict(entry_1.results) | dict(entry_2.results)

def get_sim_log_commits(sim_logs: SimulatorLogs):
    entry = SimulatorLog(sim_logs[f'sim-{date_1}'])
    return entry.accelsim_commit, entry.gpgpusim_commit

def merge_sim_log_entries():
    sim_logs = ps.get_simulator_logs(sim_logs_path)
    benchmarks = get_benchmarks_from_both(sim_logs)
    configs = get_configs(sim_logs)
    results = get_sim_log_results(sim_logs)
    commits = get_sim_log_commits(sim_logs)

    entry = ps.new_sim_log_entry()
    log_name = f'sim-{new_date}'

    entry.accelsim_commit = commits[0]
    entry.gpgpusim_commit = commits[1]
    entry.experiment = experiment_name
    entry.date = datetime.strptime(new_date, "%Y_%m_%d__%H_%M").strftime("%Y-%m-%d %H:%M")
    entry.configs = configs
    entry.benchmarks = benchmarks
    entry.results = results

    sim_logs.log_name = entry

    new_logs = {log_name: ps.sim_logs_to_dict(entry)}

    with open(os.path.expandvars(sim_logs_path), "r", encoding="utf-8") as f:
        old_logs = dict(yaml.safe_load(f)) or {}

    del old_logs[f'sim-{date_1}']
    del old_logs[f'sim-{date_2}']


    for k, v in old_logs.items():
        if k != log_name:
            new_logs[k] = ps.sim_logs_to_dict(v)



    with open(os.path.expandvars(sim_logs_path), "w", encoding="utf-8") as f:
        yaml.safe_dump(new_logs, f, sort_keys=False, allow_unicode=True)


def merge_logfiles(workload_name):
    file_1 = get_path(logfiles_path, f'{workload_name}.{date_1}.txt')
    file_2 = get_path(logfiles_path, f'{workload_name}.{date_2}.txt')
    lines = open(file_1).readlines() + open(file_2).readlines()
    for idx, line in enumerate(lines):
        lines[idx] = new_date[-5:].replace('_', ':') + ':00 ' + line[9:]

    lines = list(dict.fromkeys(lines))

    os.system(f'rm {file_1} {file_2}')

    new_file = os.path.join(logfiles_path, f'{workload_name}.{new_date}.txt')
    with open(new_file, 'a') as f:
        f.writelines(lines)

def rename_outfiles():
    sim_logs = ps.get_simulator_logs(sim_logs_path)
    entry = NS(sim_logs[f'sim-{new_date}'])
    configs = entry.configs
    for idx, config in enumerate(configs):
        configs[idx] = config.split(';;')[0]

    gpus = list(configs)
    benchmarks = get_benchmarks(sim_logs)
    for idx, benchmark in enumerate(benchmarks):
        benchmarks[idx] = benchmark.split(';')[0]

    new_o_name = f'{new_date}.o'
    new_e_name = f'{new_date}.e'

    for d in ps.iter_target_dirs(experiment_dir, gpus, benchmarks):
        o_file_1 = os.path.join(d, f'{date_1}.o')
        e_file_1 = os.path.join(d, f'{date_1}.e')
        o_file_2 = os.path.join(d, f'{date_2}.o')
        e_file_2 = os.path.join(d, f'{date_2}.e')
        new_o_path = os.path.join(d, new_o_name)
        new_e_path = os.path.join(d, new_e_name)

        existing_o_sources = []
        existing_e_sources = []
        if date_1 != new_date and os.path.exists(o_file_1):
            existing_o_sources.append(o_file_1)
        if date_2 != new_date and os.path.exists(o_file_2):
            existing_o_sources.append(o_file_2)
        if date_1 != new_date and os.path.exists(e_file_1):
            existing_e_sources.append(e_file_1)
        if date_2 != new_date and os.path.exists(e_file_2):
            existing_e_sources.append(e_file_2)

        if len(existing_o_sources) > 1:
            raise FileExistsError(
                f'Cannot rename multiple .o files to {new_o_path}: {existing_o_sources}'
            )
        if len(existing_e_sources) > 1:
            raise FileExistsError(
                f'Cannot rename multiple .e files to {new_e_path}: {existing_e_sources}'
            )

        if len(existing_o_sources) == 1 and os.path.exists(new_o_path):
            raise FileExistsError(
                f'Destination already exists while renaming output file: {new_o_path}'
            )
        if len(existing_e_sources) == 1 and os.path.exists(new_e_path):
            raise FileExistsError(
                f'Destination already exists while renaming error file: {new_e_path}'
            )

        if date_1 != new_date:
            if os.path.exists(o_file_1):
                os.rename(o_file_1, new_o_path)
            if os.path.exists(e_file_1):
                os.rename(e_file_1, new_e_path)

        if date_2 != new_date:
            if os.path.exists(o_file_2):
                os.rename(o_file_2, new_o_path)
            if os.path.exists(e_file_2):
                os.rename(e_file_2, new_e_path)

def main():
    print("Updating simulator_logs.yaml...")
    merge_sim_log_entries()

    print("Merging logfiles...")
    sim_logs = ps.get_simulator_logs(sim_logs_path)
    for benchmark in get_benchmarks(sim_logs):
        merge_logfiles(benchmark.split(';')[0])

    print("Renaming output-files...")
    rename_outfiles()
    print("Update complete")

main()
