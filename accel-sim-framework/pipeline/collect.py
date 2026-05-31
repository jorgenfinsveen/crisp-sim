#!/usr/bin/env python3

from . import *

pipeline: Pipeline = None
experiments: Experiments = None
experiment: Experiment = None
simulator_logs: SimulatorLogs = None
log: SimulatorLog = None
active_root: Path = None
key: str = None


def set_env():
    global active_root
    if pipeline.shared_mode.shared:
        active_root = os.path.expandvars(pipeline.shared_mode.root)
        result_root = os.path.expandvars(pipeline.shared_mode.results_root)
    else:
        active_root = os.getenv('CRISP_LOCAL')
        result_root = os.path.join(os.getenv('CRISP_LOCAL'), 'pipeline', 'results')
    os.environ['RESULT_ROOT'] = result_root
    os.environ['ACTIVE_ROOT'] = active_root


def parse_pipeline_config():
    global pipeline
    pipeline = get_pipeline(PIPELINE_CONFIG)
    set_env()

def parse_experiments():
    global experiments
    experiments = get_experiments(os.path.expandvars(pipeline.experiment.path))

def parse_experiment(name: str):
    global experiment
    experiment = get_experiment(name, os.path.expandvars(pipeline.experiment.path))
    experiment.results_dir = Path(os.path.expandvars(experiment.results_dir))
    experiment.logfiles = Path(os.path.expandvars(experiment.logfiles))

def parse_simlogs():
    global simulator_logs
    simulator_logs = get_simulator_logs(os.path.join(active_root, "output", "simulator_logs.yaml"))

def parse_log():
    global log
    log = simulator_logs.get(key)

    if not experiment:
        parse_experiment(log.experiment)

def select_latest():
    latest: SimulatorLog = simulator_logs.get_latest()
    latest_key = f'sim-{convert_date(latest.date, "default", "underscore")}'
    print(f"\nMost recent experiment: {latest_key}")
    print(f"\t- Name: {latest.experiment}")
    print(f"\t- Date: {latest.date}")

    while True:
        s = input("Collect this experiment [y/n]: ").strip().lower()
        if s == "y":
            global key
            key = latest_key
            return
        elif s == "n":
            return

        print("Write either y or n.")

def select_experiment():
    exp_list = experiments.get_all()

    print("\nExperiment alternatives:")
    print(35*"-")
    for i in range(len(exp_list)):
        print(f"{i+1}.\t{exp_list[i]}")

    while True:
        exp_idx = input(f"Enter experiment [1-{len(exp_list)}]: ")
        if not exp_idx.isdigit() or int(exp_idx) < 1 or int(exp_idx) > len(exp_list):
            print(f"Select a number between 1 and {len(exp_list)}.")
            continue
        experiment_name = exp_list[int(exp_idx)-1]

        parse_experiment(experiment_name)
        return

def select_date():
    logdates = simulator_logs.get_all()
    dates = []

    counter = 0
    for d in logdates:
        if (simulator_logs[d].experiment == experiment.name):
            dates.append(d.split('-')[1])
            counter += 1
        if counter == 9: break

    dates = sorted(dates, reverse=True)

    print("\nDate alternatives:")
    print(35*"-")
    for i in range(len(dates)):
        print(f"{i+1}.\t{dates[i]}")

    while True:
        date_idx = input(f"Enter date [1-{len(dates)}]: ")
        if not date_idx.isdigit() or int(date_idx) < 1 or int(date_idx) > len(dates):
            print(f"Select a number between 1 and {len(dates)}.")
            continue
        date = dates[int(date_idx)-1]

        global key
        key = f"sim-{date}"
        return

def make_export_dirs(run_id: str) -> Path:
    export_root = Path(os.path.join(experiment.results_dir, "export", experiment.name, run_id))
    export_root.mkdir(parents=True, exist_ok=True)
    return export_root


def init() -> str:
    parse_pipeline_config()
    parse_experiments()
    parse_simlogs()
    select_latest()

    if not key:
        select_experiment()
        select_date()

    parse_log()
    return key.split("-")[1]

def main():
    run_id = init()

    output_dir = os.path.join(experiment.results_dir, "output", experiment.name)
    export_dir = make_export_dirs(run_id)

    export_csv = os.path.join(export_dir, f"{run_id}.total.csv")
    export_per_sm_csv = os.path.join(export_dir, f"{run_id}.per_sm.csv")
    export_mem_partition_csv = os.path.join(export_dir, f"{run_id}.mem_partition.csv")
    executable = os.path.join(GET_STATS_SCRIPT)

    benchmarks = ",".join(experiment.benchmarks)
    configs = ",".join([config.split(";;")[0] for config in log.configs])

    stats = os.path.expandvars(os.path.join(pipeline.collect.stats_dir, f"{pipeline.collect.stats}.yml"))

    lines = []
    lines.append(SHEBANG)
    lines.append(PIPEFAIL)

    #lines.append(f'(cd $ACCEL_SIM && python3 -m pipeline.logic.cache.add_data_from_cache --directory {experiment.results_dir})\n')

    lines.append(f'mkdir -p {export_dir}\n')

    lines.append(f'{executable} \\')
    lines.append('\t-k \\')
    lines.append('\t-R \\')
    lines.append('\t-o True \\')
    lines.append(f'\t-C {configs} \\')
    lines.append(f'\t-l {experiment.logfiles}/{run_id} \\')
    lines.append(f'\t-B {benchmarks} \\')
    lines.append(f'\t-r {output_dir} \\')
    lines.append(f'\t-s {stats} \\')
    lines.append(f'\t > {export_csv}')

    lines.append(f'\npython3 {GET_STATS_PER_SM_SCRIPT} \\')
    lines.append(f'\t-r {output_dir} \\')
    lines.append(f'\t-B {benchmarks} \\')
    lines.append(f'\t-C {configs} \\')
    lines.append(f'\t-d {run_id} \\')
    lines.append(f'\t > {export_per_sm_csv}')

    lines.append(f'\npython3 {GET_STATS_MEM_PARTITION_SCRIPT} \\')
    lines.append(f'\t-r {output_dir} \\')
    lines.append(f'\t-B {benchmarks} \\')
    lines.append(f'\t-C {configs} \\')
    lines.append(f'\t-d {run_id} \\')
    lines.append(f'\t > {export_mem_partition_csv}')

    lines.append('\necho "Ferdig :)"')

    export_sh = os.path.join(experiment.results_dir, "collect.sh")
    with open(export_sh, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(f"{line}\n")


    subprocess.run(['chmod', '+x', export_sh])

    print(f"Wrote: {export_sh}")
    ans = input("Run it now? [y/n]: ").strip().lower()
    if ans == "y":
        subprocess.run(['bash', export_sh])

if __name__ == "__main__":
    main()
