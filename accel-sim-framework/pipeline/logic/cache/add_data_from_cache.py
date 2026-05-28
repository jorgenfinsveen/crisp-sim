#!/usr/bin/env python3

import os
import json
import subprocess
from pathlib import Path
from ..tools.parser import *
from ..model.simlog import *
from ..model.pipeline import *



PIPELINE: Pipeline   = None
LOGS: SimulatorLogs  = None
EXPERIMENT_DIR: Path = None
OUTPUT_ROOT: Path    = None
LOG_PATH: Path       = None
CACHE: Path          = None
EXPERIMENT: str      = None
DATE: str            = None
DATA: dict           = None

ALTERNATIVE_DATE: str = None


def init():
    global PIPELINE, OUTPUT_ROOT, LOG_PATH, CACHE, LOGS

    print()

    PIPELINE = get_pipeline()

    if PIPELINE.shared_mode.shared:
        OUTPUT_ROOT = Path(os.path.join(PIPELINE.shared_mode.results_root, "output"))
    else:
        OUTPUT_ROOT = Path(os.path.join(os.getenv("CRISP_LOCAL"), "pipeline", "results", "output"))

    CACHE = Path(os.path.join(OUTPUT_ROOT, ".cache/"))
    LOG_PATH = Path(os.path.join(OUTPUT_ROOT, "simulator_logs.yaml"))
    LOGS = get_simulator_logs(LOG_PATH)



def build_configs() -> list[str]:
    configs = []
    for gpu in DATA["configurations"]:
        s = f"{gpu};"
        cnf_file = iter_target_dirs(path=EXPERIMENT_DIR, allowed_names=[gpu])[0]
        cnf = get_config(os.path.join(cnf_file, "gpgpusim.config"))
        for parameter in DATA["parameters"]:
            s += f";{parameter}={cnf.get_value(parameter)}"
        configs.append(s)

    return configs





def build_benchmarks() -> list[str]:
    benchmarks = []

    for benchmark in DATA['benchmarks']:
        benchmarks.append(benchmark.split(':')[1])

    for idx, benchmark in enumerate(benchmarks):
        arg = get_sub_dirs_at_level_1(os.path.join(EXPERIMENT_DIR, benchmark), name_only=True)
        benchmarks[idx] += f";{';'.join(arg)}"

    return benchmarks





def build_results(benchmarks: dict) -> dict:

    def process_outfile(gpu: str, benchmark: str, argument: str) -> dict:
        global ALTERNATIVE_DATE

        out_dir = os.path.join(EXPERIMENT_DIR, benchmark, argument, gpu)
        outfile: Outfile = get_outfile(os.path.join(out_dir, f"{DATE}.o"), False)

        if not outfile and not ALTERNATIVE_DATE:
            found_date = ""
            prev_minute = int(DATE[-1]) - 1
            prev_minute = prev_minute if prev_minute >= 0 else 59
            next_minute = int(DATE[-1]) + 1
            next_minute = next_minute % 60
            alternative_date_1 = DATE[:-1] + str(prev_minute)
            alternative_date_2 = DATE[:-1] + str(next_minute)
            outfile_1 = get_outfile(os.path.join(out_dir, f"{alternative_date_1}.o"), False)
            outfile_2 = get_outfile(os.path.join(out_dir, f"{alternative_date_2}.o"), False)
            if outfile_1: found_date = alternative_date_1
            if outfile_2: found_date = alternative_date_2

            if found_date != "":
                print(f"[{EXPERIMENT}] Did not find expected out-file for {gpu} on {benchmark}:")
                print(f"\t- Expected: ...{out_dir.split("output")[1]}/{DATE}.o")
                print(f"\t- Found: ...{out_dir.split("output")[1]}/{found_date}.o")

                use_found = input("\tUse found file [y/n]: ").lower()

                if use_found[0] != "y":
                    print("\tSkipping experiment...\n")
                    return None

                ALTERNATIVE_DATE = found_date
                old = os.path.join(out_dir, f"{ALTERNATIVE_DATE}.o")
                new = os.path.join(out_dir, f"{DATE}.o")
                subprocess.run(["mv", old, new])
                outfile = get_outfile(os.path.join(out_dir, f"{DATE}.o"))
                print("")

            else:
                print(f"[{EXPERIMENT}] Did not find expected out-file for {gpu} on {benchmark}.")
                print(f"\t- Expected: ...{out_dir.split("output")[1]}/{DATE}.o")
                print("\tNo neighbouring files. Skipping...\n")
                return None

        elif not outfile and ALTERNATIVE_DATE:
            outfile = get_outfile(os.path.join(out_dir, f"{ALTERNATIVE_DATE}.o"), False)
            if not outfile:
                print(f"[{EXPERIMENT}] Second time not found out-file for {gpu} on {benchmark}. Tried:")
                print(f"\t1: ...{out_dir.split("output")[1]}/{DATE}.o")
                print(f"\t2: ...{out_dir.split("output")[1]}/{ALTERNATIVE_DATE}.o")
                print("\tSkipping experiment...\n")
                return None

        arg = {}
        arg["none"] = outfile.get_node()
        for var in DATA["result_variables"]:
            arg[var] = "REPLACE_VALUE"

        return arg


    def build_for_benchmark(gpu, benchmark, arguments) -> dict:
        bench = {}

        for argument in arguments:
            data = process_outfile(gpu, benchmark, argument)
            if not data: return None
            bench[argument] = data

        return bench

    def build_for_gpu(name: str, benchmarks: list[str]) -> dict:
        gpu = {}

        for benchmark in benchmarks:
            data = build_for_benchmark(name, benchmark.split(";")[0], benchmark.split(";")[1:])
            if not data: return None
            gpu[benchmark] = data

        return gpu

    results = {}

    for gpu in DATA['configurations']:
        data = build_for_gpu(gpu, benchmarks)
        if not data: return None
        results[gpu] = data

    return results



def add_to_logs(cache_entry: Path) -> bool:
    global LOGS, DATA, DATE, EXPERIMENT, EXPERIMENT_DIR

    with open(file=cache_entry, mode="r", encoding="utf-8") as f:
        DATA = dict(json.load(f)) or {}

    DATE = cache_entry.name.split(".")[0]
    EXPERIMENT = DATA["experiment"]
    EXPERIMENT_DIR = os.path.join(OUTPUT_ROOT, EXPERIMENT)

    benchmarks = build_benchmarks()
    configs     = build_configs()
    results    = build_results(benchmarks)

    actual_date = DATE if not ALTERNATIVE_DATE else ALTERNATIVE_DATE
    log_name = f"sim-{actual_date}"

    if log_name in LOGS.keys():
        entry = LOGS[log_name]
    else:
        entry = new_sim_log_entry()
        LOGS[log_name] = entry

    if not results: return False

    entry.accelsim_commit = DATA['accelsim_commit']
    entry.gpgpusim_commit = DATA['gpgpusim_commit']
    entry.experiment      = EXPERIMENT
    entry.date            = convert_date(actual_date, "underscore", "default")
    entry.configs          = configs
    entry.benchmarks      = benchmarks
    entry.results         = results


    LOGS = insert_entry_to_sim_log(log_name, entry, LOGS)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(LOGS, f, sort_keys=False, allow_unicode=True)

    return True


def main():
    global ALTERNATIVE_DATE
    processed = []
    for entry in CACHE.glob("*.json"):
        try:
            date = entry.name.split(".")[0]
            if add_to_logs(entry):
                actual_date = date if not ALTERNATIVE_DATE else ALTERNATIVE_DATE
                processed.append((actual_date, True))
                subprocess.run(["rm", entry])
            else:
                processed.append((date, False))
        except Exception as e:
            print(f"Error occured when processing {entry.name}. Skipping...\n")
        ALTERNATIVE_DATE = None

    if len(processed) != 0:
        print(f"\nProcessed cached data for {LOG_PATH}:")
        for tup in processed:
            s = "✓" if tup[1] else "x"
            print(f"\t{s} {tup[0]}")

if __name__ == "__main__":
    init()
    main()
