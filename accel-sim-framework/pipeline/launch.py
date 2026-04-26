#!/usr/bin/env python3

from . import *

argparser = argparse.ArgumentParser()
argparser.add_argument("--run", required=False, help="Run jobs right away?")
args = argparser.parse_args()
if (args.run): args.run = args.run.strip()


pipeline = {}
traces = {}
experiment = {}


def set_env():
    if pipeline.shared_mode.shared:
        active_root = os.path.expandvars(pipeline.shared_mode.root)
        result_root = os.path.expandvars(pipeline.shared_mode.results_root)
    else:
        active_root = os.getenv('CRISP_LOCAL')
        result_root = os.path.join(active_root, 'pipeline', 'results')
    subprocess.run(['export', f'RESULT_ROOT={result_root}'])
    subprocess.run(['export', f'ACTIVE_ROOT={active_root}'])



def parse_pipeline_config():
    global pipeline
    pipeline = get_pipeline()
    pipeline.trace_lookup = Path(os.path.expandvars(pipeline.trace_lookup))
    for dest in pipeline.config_destinations:
        pipeline.config_destinations[dest] = Path(os.path.expandvars(pipeline.config_destinations[dest]))
    arr = []
    for instance in pipeline.instances:
        arr.append(instance.replace("-", "_"))
    pipeline.instances = arr
    set_env()



def parse_traces():
    global traces
    traces = get_traces(pipeline.trace_lookup)
    for trace in traces.get_all():
        traces[trace] = os.path.expandvars(traces[trace])

def parse_experiment():
    global experiment
    experiment = get_experiment(pipeline.experiment.name, os.path.expandvars(pipeline.experiment.path))
    experiment.results_dir = Path(os.path.expandvars(experiment.results_dir))
    experiment.logfiles = Path(os.path.expandvars(experiment.logfiles))



def prepare_instance(instance):
    src_dir = os.path.join(CONFIGURATIONS_ROOT, instance)
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
    subprocess.run(['mkdir', '-p', dest.gpgpusim, dest.trace])

    gpgpusim_target = os.path.join(dest.gpgpusim, instance)
    trace_target = os.path.join(dest.trace, instance)

    subprocess.run(['rsync', '-av', '--exclude="trace.config"', f'{src_dir}/', f'{gpgpusim_target}/'])
    subprocess.run(['rsync', '-av', f'{src_dir}/trace.config', f'{trace_target}/'])

    new_line = f'    base_file: "{gpgpusim_target}/gpgpusim.config"\n'

    with open(STANDARD_CONFIGURATIONS, "r") as f: data = yaml.safe_load(f) or {}

    if instance not in data:
        with open(STANDARD_CONFIGURATIONS, "a") as f: f.write(f"\n\n{instance}:\n{new_line}")
    else:
        with open(STANDARD_CONFIGURATIONS, "r") as f: lines = f.readlines()

        key_line = f"{instance}:"
        for i, line in enumerate(lines[:-1]):
            if line.lstrip().startswith(key_line):
                lines[i + 1] = new_line
                break

        with open(STANDARD_CONFIGURATIONS, "w") as f:
            f.writelines(lines)

    return True


def build_command(benchmark, instance=None, aggregate=False):
    cmd = []
    experiment_dir = os.path.join(experiment.results_dir, 'output', experiment.name)
    instance = '$(date +"%Y_%m_%d__%H_%M")' if not instance else instance
    extra_configs = '-'.join(pipeline.extra_configs)
    instance_configs = ",".join(f"{i}-{extra_configs}" \
        for i in pipeline.instances )if aggregate else f"{instance}-{extra_configs}"

    cmd.append(RUN_SIMULATIONS_SCRIPT)
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
    cmd.append(CACHE_LAUNCH_DATA_SCRIPT)
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
        f.write(SHEBANG)
        f.write(PIPEFAIL)
        f.write(LAUNCH_DATE)
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
    subprocess.run(['chmod', '+x', export_path])

    print(f'\n\nScript to start simulator-instances written to: \n - {export_path}')

    if (args.run):
        subprocess.run(['bash', export_path])
        return

    while True:
        ans = input('\nStart instances now (y/n): ').strip()
        if ans.casefold() == 'y'.casefold(): subprocess.run(['bash', export_path]); break
        elif ans.casefold() == 'n'.casefold(): break
        else: print('Invalid input, please write y or n.')


if __name__ == "__main__":
    main()
