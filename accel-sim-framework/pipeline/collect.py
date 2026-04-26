#!/usr/bin/env python3

from . import *

pipeline = {}
experiment = {}

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=False, help="Date of the run to collect [YYYY_mm_DD__HH_MM].")
parser.add_argument("--experiment", required=False, help="Name of an experiment to get the latest run from.")
args = parser.parse_args()

def set_env():
    if pipeline.shared_mode.shared:
        active_root = os.path.expandvars(pipeline.shared_mode.root)
        result_root = os.path.expandvars(pipeline.shared_mode.results_root)
    else:
        active_root = os.getenv('CRISP_LOCAL')
        result_root = os.path.join(os.getenv('CRISP_LOCAL'), 'pipeline', 'results')
    subprocess.run(['export', f'RESULT_ROOT={result_root}'])
    subprocess.run(['export', f'ACTIVE_ROOT={active_root}'])


def parse_pipeline_config():
    global pipeline
    pipeline = get_pipeline(PIPELINE_CONFIG)
    set_env()


def parse_experiment(name):
    global experiment
    name = name if name else pipeline.experiment.name
    experiment = get_experiment(name, pipeline.experiment.path)
    experiment.results_dir = Path(os.path.expandvars(experiment.results_dir))
    experiment.logfiles = Path(os.path.expandvars(experiment.logfiles))


def main():
    global pipeline
    parse_pipeline_config()
    parse_experiment(args.experiment)
    if not args.date:
        path = os.path.join(experiment.results_dir, 'output', 'simulator_logs.yaml')
        sim_logs = get_simulator_logs(path)
        exp_name = args.experiment.strip() if args.experiment else ""
        log = sim_logs.get_latest(exp_name)
        run_id = convert_date(log.date, "default", "underscore")
        substr = f"results from {exp_name}" if exp_name != "" else ""
        print(f"Latest {substr}: sim-{run_id}")
    else:
        run_id = args.date.strip()


    output_dir = os.path.join(experiment.results_dir, "output", experiment.name)
    export_dir = os.path.join(experiment.results_dir, "export", "total")

    export_csv = os.path.join(export_dir, f"{run_id}.csv")
    executable = os.path.join(GET_STATS_SCRIPT)

    benchmarks = ",".join(experiment.benchmarks)
    configs = ",".join(pipeline.instances)

    lines = []
    lines.append(SHEBANG)
    lines.append(PIPEFAIL)

    lines.append(f'mkdir -p {export_dir}\n')

    lines.append(f'{executable} \\')
    lines.append('\t-k \\')
    lines.append('\t-R \\')
    lines.append('\t-o True \\')
    lines.append(f'\t-C {configs} \\')
    lines.append(f'\t-l {experiment.logfiles}/{run_id} \\')
    lines.append(f'\t-B {benchmarks} \\')
    lines.append(f'\t-r {output_dir} \\')
    lines.append(f'\t > {export_csv}')

    lines.append('\necho "Ferdig :)"')

    export_sh = os.path.join(experiment.results_dir, "collect.sh")
    with open(export_sh, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(f"{line}\n")


    subprocess.run(['chmod', '+x', export_sh])

    print(f"Wrote: {export_sh}")
    ans = input("Run it now? [y/N]: ").strip().lower()
    if ans == "y":
        subprocess.run(['bash', export_sh])
    run_csv_generator = input("Run csv generator for the test result? [y/N]: ")
    if run_csv_generator == "y":
        subprocess.run(CALL_COLLECT_CSV_SCRIPT)

if __name__ == "__main__":
    main()
