#!/usr/bin/env python3

import os
import json
import argparse
import subprocess
from pathlib import Path
from ..tools.parser import *
from ..model.simlog import *

argparser = argparse.ArgumentParser()
argparser.add_argument("--directory", required=False, help="Directory of simulator output.")
args = argparser.parse_args()
args.directory = os.path.expandvars(args.directory)


CACHE = Path(os.path.join(args.directory, '.cache/'))
LOG_PATH  = Path(os.path.join(args.directory, 'simulator_logs.yaml'))

LOGS: SimulatorLogs = get_simulator_logs(LOG_PATH)

data = {}
date = ""
experiment = ""
experiment_dir: Path = ""


def build_configs() -> dict:
    configs = []
    for gpu in data["configurations"]:
        s = f"{gpu};"
        cnf_file = iter_target_dirs(path=experiment_dir, allowed_names=[gpu])[0]
        cnf = get_config(os.path.join(cnf_file, "gpgpusim.config"))
        for parameter in data["parameters"]:
            s += f";{parameter}={cnf.get_value(parameter)}"
        configs.append(s)

    return configs





def build_benchmarks() -> list:
    benchmarks = []

    for benchmark in data['benchmarks']:
        benchmarks.append(benchmark.split(':')[1])

    for idx, benchmark in enumerate(benchmarks):
        arg = get_sub_dirs_at_level_1(os.path.join(experiment_dir, benchmark), name_only=True)
        benchmarks[idx] += f";{';'.join(arg)}"

    return benchmarks





def build_results(benchmarks: dict) -> dict:

    def build_for_benchmark(gpu, benchmark, arguments) -> dict:
        bench = {}

        for argument in arguments:
            arg = {}
            outfile = get_outfile(os.path.join(experiment_dir, benchmark, argument, gpu, f"{date}.o"))
            arg["node"] = outfile.get_node()

            for var in data["result_variables"]:
                arg[var] = "REPLACE_VALUE"

            bench[argument] = arg

        return bench

    def build_for_gpu(name: str, benchmarks: list[str]) -> dict:
        gpu = {}

        for benchmark in benchmarks:
            gpu[benchmark] = build_for_benchmark(name, benchmark.split(";")[0], benchmark.split(";")[1:])

        return gpu

    results = {}

    for gpu in data['configurations']:
        results[gpu] = build_for_gpu(gpu, benchmarks)

    return results



def add_to_logs(cache: Path):
    global LOGS, data, date, experiment, experiment_dir
    with open(file=cache, mode="r", encoding="utf-8") as f:
        data = dict(json.load(f)) or {}

    date = cache.name.split(".")[0]
    experiment = data["experiment"]
    experiment_dir = os.path.join(args.directory, experiment)

    log_name = f"sim-{date}"

    if log_name in LOGS.get_all():
        entry = LOGS[log_name]
    else:
        entry = new_sim_log_entry()
        LOGS.log_name = entry

    benchmarks = build_benchmarks()
    configs = build_configs()
    results = build_results(benchmarks)


    entry.accelsim_commit = data['accelsim_commit']
    entry.gpgpusim_commit = data['gpgpusim_commit']
    entry.experiment      = experiment
    entry.date            = convert_date(date, "underscore", "default")
    entry.configs          = configs
    entry.benchmarks      = benchmarks
    entry.results         = results


    LOGS = insert_entry_to_sim_log(log_name, entry, LOGS)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(LOGS, f, sort_keys=False, allow_unicode=True)


def main():
    for cache in CACHE.glob("*.json"):
        add_to_logs(cache)
        subprocess.run(["rm", cache])

if __name__ == "__main__":
    main()
