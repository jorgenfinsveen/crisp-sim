from . import *

class SimulatorLog:
    def __init__(self, obj: SimpleNamespace):
        self._obj = obj

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(vars(self._obj).keys()))

    def __repr__(self):
        items = {
            k: v for k, v in vars(self._obj).items()
            if (not k.startswith("_") and not callable(v))
        }
        return repr(items)

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def __getitem__(self, key):
        return getattr(self._obj, key)

    def __setitem__(self, key, value):
        setattr(self._obj, key, value)

    def __contains__(self, key):
        return hasattr(self._obj, key)

    def get(self, key, default=None):
        return getattr(self._obj, key, default)

    def get_all(self) -> list[str]:
        return self._obj.get_all()

    def get_benchmarks(self) -> dict:
        return self._obj.get_benchmarks()

    def get_configs(self) -> dict:
        return self._obj.get_configs()

    def get_results(self, config: str, app: str) -> dict:
        return self._obj.get_results(config, app)


class SimulatorLogs:
    def __init__(self, obj: SimpleNamespace, path: Path=None):
        self._obj = obj
        self._path = path

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(vars(self._obj).keys()))

    def __repr__(self):
        items = {
            k: v for k, v in vars(self._obj).items()
            if (not k.startswith("_") and not callable(v))
        }
        return repr(items)

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def __getitem__(self, key):
        return to_namespace(getattr(self._obj, key))

    def __setitem__(self, key, value: SimulatorLog):
        # if isinstance(value, SimulatorLog):
        #     setattr(self._obj, key, value._obj)
        # else:
        #     setattr(self._obj, key, value)
        setattr(self._obj, key, to_namespace(value._obj))

    def __contains__(self, key):
        return hasattr(self._obj, key)

    def get(self, key, default=None):
        return getattr(self._obj, key, default)

    def get_all(self) -> list[str]:
        return self._obj.get_all()

    def get_latest(self, experiment: str=""):
        return self._obj.get_latest(experiment)

    def get_oldest(self, experiment: str=""):
        return self._obj.get_oldest(experiment)

    def get_path(self) -> Path:
        return self._path

    def get_name(self) -> str:
        return self._path.name




def to_simulator_log(log: SimpleNamespace) -> NS:
    obj = to_namespace(log)

    def get_benchmarks(self) -> dict:
        bm = {}
        for entry in self.benchmarks:
            parts = entry.split(';')
            bm[parts[0]] = parts[1:]
        return bm

    def get_configs(self) -> dict:
        cfgs = {}
        for entry in self.configs:
            parts = entry.split(';;')
            cfgs[parts[0]] = {}
            for param in parts[1:]:
                cfgs[parts[0]][param.split('=')[0]] = param.split('=')[1]
        return cfgs

    def get_results(self, config: str, app: str) -> dict:
        return to_dict(self.results.__dict__[config].__dict__[app])

    for name, fn in locals().items():
        if callable(fn) and name not in {"simulator_log", "obj"}:
            obj = add_method(obj, name, fn)

    return SimulatorLog(obj)


def get(simulator_logs: dict, path: Path=None) -> NS:
    obj = to_namespace(simulator_logs)

    def get_latest(self, experiment: str="") -> SimulatorLog:
        if experiment == "":
            return to_simulator_log(getattr(self, max(self.get_all())))
        experiments = [exp for exp in self.get_all() if f'sim-{exp}' in self.get_all()]
        return to_simulator_log(getattr(self, max(experiments)))


    def get_oldest(self, experiment: str="") -> NS:
        if experiment == "":
            return to_simulator_log(getattr(self, min(self.get_all())))
        experiments = [exp for exp in self.get_all() if f'sim-{exp}' in self.get_all()]
        return to_simulator_log(getattr(self, min(experiments)))

    for name, fn in locals().items():
        if callable(fn) and name not in {"simulator_logs", "obj"}:
            obj = add_method(obj, name, fn)

    return SimulatorLogs(obj, path)

def new_log(path: Path=None) -> NS:
    return get({}, path)

def new_sim_log_entry() -> NS:
    return to_namespace({})
