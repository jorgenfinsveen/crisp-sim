#!/usr/bin/env python3

import os
import sys
import yaml
import time
import argparse
import utility.parser as ps

from pathlib import Path
from datetime import datetime

# THIS_DIR: Path  = Path(__file__).resolve().parent
# sys.path.append(str(THIS_DIR))


parser = argparse.ArgumentParser(description="Parameters to pass to the script.")
parser.add_argument("--target", required=True, help="Datetime to search for in the logs. Format: %Y_%m_%d__%H_%M")
parser.add_argument("--logs", required=True, help="Absolute path to simulator_logs.yaml.")
parser.add_argument("--pipeline", required=True, help="Absolute path to pipeline.yaml.")
parser.add_argument("--no_sleep", required=False, help="Set to false to prevent 10 second sleep.")
args = parser.parse_args()

logs = {}
'''Dictionary of the contents of simulator_logs.yaml'''

target = {}
'''Sub-dictionary of the contents of simulator_logs.yaml'''

pipeline = {}
'''Dictionary of the contents of pipeline.yaml'''

experiment = {}

hashes = {}

def nonexistent_error(filename, filepath):
    gpgpusim_root = os.getenv("GPGPUSIM_ROOT")
    error_logs = os.path.join(gpgpusim_root, "../../pipeline/logs/update_logs.err")
    with open(error_logs, "a",encoding="utf-8") as f:
        f.write(f"[{args.target}] unable to find {filename} at: {filepath}")
    print(f"[{args.target}] unable to find {filename} at: {filepath}")
    sys.exit(1)


def parse_sim_logs():
    global logs
    path = os.path.expandvars(args.logs)
    if not os.path.exists(path):
        Path(path).touch()

    logs = ps.get_simulator_logs(path)


def parse_pipeline_config():
    global pipeline
    pipeline = ps.get_pipeline(args.pipeline)


def parse_experiment():
    global experiment
    experiment = ps.get_experiment(pipeline.experiment.name, pipeline.experiment.path)
    experiment.results_dir = Path(os.path.expandvars(experiment.results_dir))
    experiment.logfiles = Path(os.path.expandvars(experiment.logfiles))


def collect_instance_stats(root, param_fields, result_fields, allowed_names: list[str], benchmarks: list[str]) -> tuple[list, list, dict]:
    global hashes
    root = Path(root)

    results = {}
    configs = []
    apps = []
    apps_d = {}

    for i in range(len(benchmarks)):
        benchmarks[i] = benchmarks[i].split(':')[1]

    for d in ps.iter_target_dirs(root, allowed_names, benchmarks):
        out = ps.get_outfile(os.path.join(d, f"{args.target}.o"))
        cnf = ps.get_config(os.path.join(d, 'gpgpusim.config'))

        config = cnf.get_config()
        param = cnf.get_benchmark()
        app   = cnf.get_app()

        if hashes == {}:
            hashes = out.get_commit_hashes()

        if not any(config in c for c in configs):
            #entry = f"{config.split('_')[0]};"
            entry = f"{config};"
            for field in param_fields:
                val = cnf.get_value(field)
                entry += f";{field}="
                entry += str(val) if val is not None else str(-1)
            configs.append(entry)

        if app not in apps_d:
            apps_d[app] = [app]

        if param not in list(apps_d[app]):
            apps_d[app].append(f"{param}")

        param = param.lstrip("_")

        if config not in allowed_names:
            continue

        if config not in results:
            results[config] = {}

        if app not in results[config]:
            results[config][app] = {}

        if param not in results[config][app]:
            results[config][app][param] = {}

        results[config][app][param]["node"] = out.get_node()

        for field in result_fields:
            results[config][app][param][field] = "REPLACE_VALUE"

    for entry in apps_d.values():
        s = ""
        for part in entry:
            s += part + ";"
        apps.append(s[:-1])
    return configs, apps, results


def main():
    if not args.no_sleep:
        time.sleep(60)
    parse_sim_logs()
    parse_pipeline_config()
    parse_experiment()

    global logs, target
    if logs is None:
        logs = ps.new_sim_log(os.path.expandvars(args.logs))

    log_name = f"sim-{args.target}"

    if log_name in logs.get_all():
        target = logs[log_name]
    else:
        target = ps.new_sim_log_entry()
        logs.log_name = target

    instances      = pipeline.instances
    benchmarks     = experiment.benchmarks
    param_fields    = experiment.params
    result_fields   = experiment.results
    root           = f"{os.path.expandvars(experiment.results_dir)}/output/{experiment.name}"
    configs, benchmarks, results = collect_instance_stats(root, param_fields, result_fields, instances, benchmarks)

    target.accelsim_commit = hashes['accelsim_commit']
    target.gpgpusim_commit = hashes['gpgpusim_commit']
    target.experiment      = experiment.name
    target.date            = datetime.strptime(args.target, "%Y_%m_%d__%H_%M").strftime("%Y-%m-%d %H:%M")
    target.configs          = configs
    target.benchmarks      = benchmarks
    target.results         = results

    new_logs = {log_name: ps.sim_logs_to_dict(target)}

    for k, v in logs.items():
        if k != log_name:
            new_logs[k] = ps.sim_logs_to_dict(v)

    with open(os.path.expandvars(args.logs), "w", encoding="utf-8") as f:
        yaml.safe_dump(new_logs, f, sort_keys=False, allow_unicode=True)


main()
