#!/usr/bin/env python3

import os
import yaml
import argparse
import importlib.util
from pathlib import Path

DIR_PATH: Path = Path(__file__).resolve().parent
SIM_CONFIGS_DIR: Path = os.path.join(DIR_PATH, "configs")
PIPELINE_CONFIG_FILE: Path = os.path.join(DIR_PATH, "setup", "pipeline.yaml")

PARSER: Path = os.path.join(DIR_PATH, "utility", "parser.py")
spec = importlib.util.spec_from_file_location("parser", PARSER)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


argparser = argparse.ArgumentParser()
argparser.add_argument("--run", required=False, help="Run jobs right away?")
args = argparser.parse_args()
if (args.run): args.run = args.run.strip()


pipeline = {}
traces = {}
experiment = {}

def parse_pipeline_config():
    global pipeline
    pipeline = parser.get_pipeline()
    pipeline.trace_lookup = Path(os.path.expandvars(pipeline.trace_lookup))
    for dest in pipeline.config_destinations:
        pipeline.config_destinations[dest] = Path(os.path.expandvars(pipeline.config_destinations[dest]))
    arr = []
    for instance in pipeline.instances:
        arr.append(instance.replace("-", "_"))
    pipeline.instances = arr


def parse_traces():
    global traces
    traces = parser.get_traces(pipeline.trace_lookup)
    for trace in traces.get_all():
        traces[trace] = os.path.expandvars(traces[trace])

def parse_experiment():
    global experiment
    experiment = parser.get_experiment(pipeline.experiment.name, pipeline.experiment.path)
    experiment.results_dir = Path(os.path.expandvars(experiment.results_dir))
    experiment.logfiles = Path(os.path.expandvars(experiment.logfiles))


def prepare_instance(instance):
    src_dir = os.path.join(SIM_CONFIGS_DIR, instance)
    src_config = os.path.join(src_dir, 'gpgpusim.config')
    src_trace = os.path.join(src_dir, 'trace.config')

    missing_handlers = {
        src_dir:   lambda: print(f'Skipping {instance} due to missing dir: {src_dir}'),
        src_config: lambda: print(f'Skipping {instance} due to missing file: {src_config}'),
        src_trace: lambda: print(f'Skipping {instance} due to missing file: {src_trace}')
    }

    for path, handler in missing_handlers.items():
        if not os.path.exists(path):
            handler()
            return False

    dest = pipeline.config_destinations
    os.system(f"mkdir -p {Path(dest.gpgpusim)} {Path(dest.trace)}")

    gpgpusim_target = os.path.join(dest.gpgpusim, instance)
    trace_target = os.path.join(dest.trace, instance)

    os.system(f"rsync -av --exclude='trace.config' '{src_dir}/' '{gpgpusim_target}/'")
    os.system(f"rsync -av '{src_dir}/trace.config' '{trace_target}/'")


    cfgs_yml = os.path.expandvars("$ACCEL_SIM/" \
        "util/job_launching/configs/define-standard-cfgs.yml"
    )

    new_line = f'    base_file: "{gpgpusim_target}/gpgpusim.config"\n'

    with open(cfgs_yml, "r") as f:
        data = yaml.safe_load(f) or {}

    if instance not in data:
        with open(cfgs_yml, "a") as f:
            f.write(f"\n\n{instance}:\n{new_line}")
    else:
        with open(cfgs_yml, "r") as f:
            lines = f.readlines()

        key_line = f"{instance}:"
        for i, line in enumerate(lines[:-1]):
            if line.lstrip().startswith(key_line):
                lines[i + 1] = new_line
                break

        with open(cfgs_yml, "w") as f:
            f.writelines(lines)

    return True


def build_command(benchmark, instance=None, aggregate=False):
    cmd = []
    experiment_dir = os.path.join(experiment.results_dir, 'output', experiment.name)
    instance = '$(date +"%Y_%m_%d__%H_%M")' if not instance else instance
    extra_configs = '-'.join(pipeline.extra_configs)
    instance_configs = ",".join(f"{i}-{extra_configs}" \
        for i in pipeline.instances )if aggregate else f"{instance}-{extra_configs}"

    cmd.append(os.path.expandvars("$ACCEL_SIM/util/job_launching/run_simulations.py"))
    cmd.append(f"--override_names {pipeline.override_names}")
    cmd.append(f"--job_mem {pipeline.job_mem}")
    cmd.append(f"--launcher {pipeline.launcher}")
    cmd.append(f"--benchmark_list {benchmark}")
    cmd.append(f"--trace_dir {traces[benchmark.split(':')[0]]}")
    cmd.append(f"--launch_name {pipeline.name_prefix}-$launch_date")
    cmd.append(f"--run_directory {experiment_dir}")
    cmd.append(f"--logfile_dir_dest {experiment.logfiles}")
    cmd.append(f"--configs_list {instance_configs}")

    return cmd


def build_cache_command():
    directory = os.path.join(experiment.results_dir, 'output')
    benchmarks = ",".join(i for i in experiment.benchmarks)
    parameters = ",".join(i for i in experiment.params)
    configurations = ",".join(i for i in pipeline.instances)
    result_variables = ",".join(i for i in experiment.results)

    cmd = []
    cmd.append(os.path.expandvars('$ACCEL_SIM/pipeline/utility/cache_launch_data.py'))
    cmd.append('--date $launch_date')
    cmd.append(f'--experiment {experiment.name}')
    cmd.append(f'--accelsim_commit {os.getenv("ACCELSIM_COMMIT")}')
    cmd.append(f'--gpgpusim_commit {os.getenv("GPGPUSIM_COMMIT")}')
    cmd.append(f'--directory {directory}')
    cmd.append(f'--benchmarks {benchmarks}')
    cmd.append(f'--parameters {parameters}')
    cmd.append(f'--configurations {configurations}')
    cmd.append(f'--result_variables {result_variables}')

    return cmd



def export_commands(commands, path):
    with open(path, 'w') as f:
        f.write('#!/usr/bin/env bash\n')
        f.write('set -euo pipefail\n\n')
        f.write(f'launch_date=$(date +"%Y_%m_%d__%H_%M")\n\n')
        for command in commands:
            cmd = command[0] + ' \\\n'
            for i in range(1, len(command)):
                cmd += '\t' + command[i] + ' \\\n'
            f.write(cmd[:-3] + '\n\n')

        for num, line in enumerate(build_cache_command()):
            f.write('\t' + line + ' \\\n' if num > 0 else line + ' \\\n')



def ensure_dirs_present():
    for d in [experiment.results_dir]:
        os.makedirs(d, exist_ok=True)


def main():
    global pipeline
    custom_setup_was_run = os.getenv('CUSTOM_SETUP_ENVIRONMENT_WAS_RUN')
    if not custom_setup_was_run or int(custom_setup_was_run) != 1:
        path = os.path.join(DIR_PATH.parent, 'setup_environment.sh')
        if os.path.exists(path):
            os.system(f'source {path}')

    parse_pipeline_config()
    parse_traces()
    parse_experiment()
    ensure_dirs_present()

    commands = []
    pipeline.instances[:] = [
        inst for inst in pipeline.instances
        if prepare_instance(inst)
    ]

    if pipeline.aggregate:
        for benchmark in experiment.benchmarks: commands.append(build_command(benchmark, aggregate=True))
    else:
        for inst in pipeline.instances:
            for benchmark in experiment.benchmarks: commands.append(build_command(benchmark, instance=inst))

    export_path = os.path.join(experiment.results_dir, 'launch.sh')
    export_commands(commands, export_path)
    os.system(f"chmod +x {export_path}")

    print(f'\n\nScript to start simulator-instances written to: \n - {export_path}')

    if (args.run):
        os.system(f'bash {export_path}')
        return

    while True:
        ans = input('\nStart instances now (y/n): ').strip()
        if ans.casefold() == 'y'.casefold(): os.system(f'bash {export_path}'); break
        elif ans.casefold() == 'n'.casefold(): break
        else: print('Invalid input, please write y or n.')

main()
