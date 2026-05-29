#!/usr/bin/env python3

from . import *

def nonexistent_error(path: Path) -> FileNotFoundError:
    raise FileNotFoundError(f"File not found: {path}")


def assert_file_exists(path: Path, exception=True) -> Path:
    path = Path(os.path.expandvars(str(path).strip()))
    if os.path.exists(path):
        return path
    if not exception:
        return None
    nonexistent_error(path)


def get_pipeline(path: Path="") -> Pipeline:
    if path == "":
        path = PIPELINE_CONFIG

    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:
        pl = yaml.safe_load(f) or {}
        return pipeline_get(pl, path)

def get_experiments(path: Path="") -> Experiments:
    if path == "":
        path = get_pipeline().experiment.path

    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:
        exp = yaml.safe_load(f) or {}
        return experiment_get(exp, path)

def get_experiment(name: str, path: Path="") -> Experiment:
    if path == "":
        path = get_pipeline().experiment.path

    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:
        exps = yaml.safe_load(f) or {}
        exps = experiment_get(exps, path)
        return extract_experiment(exps, name.strip())


def get_traces(path: Path="") -> Traces:
    if path == "":
        path = get_pipeline().trace_lookup

    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:
        tr = yaml.safe_load(f) or {}
        return traces_get(tr, path)


def get_simulator_logs(path: Path="") -> SimulatorLogs:
    if path == "":
        results_dir = os.path.expandvars(get_pipeline().results_dir)
        path = os.path.join(results_dir, 'output', 'simulator_logs.yaml')

    path = assert_file_exists(path)

    with open(path, 'r', encoding='utf-8') as f:
        sl = yaml.safe_load(f) or {}
        return simlog_get(sl, path)


def get_config(path: Path) -> Config:
    path = assert_file_exists(path)
    return config_get(path)


def get_outfile(path: Path, throw_exception: bool=True) -> Outfile|None:
    path = assert_file_exists(path, throw_exception)
    if not path: return None
    return outfile_get(path)


def iter_target_dirs(path: Path, allowed_names: Iterable[str], allowed_subnames: Iterable[str]=None) -> list[Path]:
    path = assert_file_exists(path)
    allowed = set(allowed_names)
    dirs = []
    for d in path.rglob("*"):
        #print(d)
        if d.is_dir() and d.name in allowed:
            if not allowed_subnames:
                dirs.append(d)
            elif any(x in allowed_subnames for x in d.parts):
                dirs.append(d)
    return dirs

def get_sub_dirs_at_level_1(path: Path, ignore_names: Iterable[str]=[], name_only=False) -> list[Path|str]:
    path = assert_file_exists(path)
    ignore = set(ignore_names)
    dirs = []
    for inode in path.glob("*"):
        if inode.name not in ignore and inode.is_dir():
            dirs.append(inode if not name_only else inode.name)
    return dirs



def search_in_string(s: str, start: str, end: Optional[str] = None) -> str:
    i = s.find(start)
    if i == -1:
        return ""
    start_idx = i + len(start)
    if end is None:
        return s[start_idx:]
    j = s.find(end, start_idx)
    return s[start_idx:j] if j != -1 else ""


def extract_commit_hashes(s: str) -> dict:
    return {
        'accelsim-commit': search_in_string(s, "accelsim-commit-", "gpgpu-sim_git-commit-"),
        'gpgpusim-commit': search_in_string(s, "gpgpu-sim_git-commit-")
    }

def get_line(path: Path, prefix: str, n=350):
    path = assert_file_exists(path)
    prefix = prefix.strip()
    if prefix == '' or prefix == '-':
        return None
    BYTES_TO_READ = int(250 * 1024 * 1024)
    count = 0
    with open(path, 'r', encoding='utf-8') as f:
        fsize = int(os.stat(path).st_size)
        if fsize > BYTES_TO_READ:
            f.seek(0, os.SEEK_END)
            f.seek(f.tell() - BYTES_TO_READ, os.SEEK_SET)
        lines = f.readlines()
        for line in lines:
            if not line or line.startswith('#'):
                continue
            count += 1
            if count >= n:
                return None
            if line.startswith(prefix):
                return line.strip()
        return None

def new_sim_log(path: Path=None) -> SimulatorLogs:
    return new_log(path)

def new_sim_log_entry() -> NS:
    return sim_log_new_entry()

def sim_logs_to_dict(x) -> dict:
    if hasattr(x, "_obj"):
        x = x._obj
    return namespace_to_dict(x)

def insert_entry_to_sim_log(name: str, entry: NS, sim_log: SimulatorLogs) -> dict:
    new_logs = {name: sim_logs_to_dict(entry)}

    for k, v in sim_log.items():
        if k != name:
            new_logs[k] = sim_logs_to_dict(v)

    return new_logs

def remove_entries_from_sim_log(entries: list[str], sim_log: SimulatorLogs) -> dict:
    sim_log = namespace_to_dict(sim_log)
    missing_keys = [key for key in entries if key not in sim_log]
    if missing_keys:
        available_keys = sorted(key for key in sim_log.keys() if str(key).startswith("sim-"))
        raise KeyError(
            "Cannot merge experiment dates because the following simulator log entries were not found: "
            + ", ".join(missing_keys)
            + ". Available simulator log entries: "
            + (", ".join(available_keys) if available_keys else "<none>")
        )

    for key in entries:
        del sim_log[key]
    return sim_log



def convert_date(date_str: str, old_format: str, new_format: str) -> str:
    f1 = "%Y_%m_%d__%H_%M" if old_format == "underscore" else "%Y-%m-%d %H:%M"
    f2 = "%Y-%m-%d %H:%M" if new_format == "default" else "%Y_%m_%d__%H_%M"
    return datetime.strptime(date_str, f1).strftime(f2)
