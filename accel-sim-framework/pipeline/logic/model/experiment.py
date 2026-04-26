from . import *


class Experiment:
    def __init__(self, obj: SimpleNamespace, name: str):
        self._obj = obj
        self._obj.name: str = name  # pyright: ignore[reportInvalidTypeForm]

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

    def get_apps(self) -> dict:
        return self._obj.get_benchmarks()

    def get_results(self) -> dict:
        return self._obj.get_results()

    def get_params(self) -> dict:
        return self._obj.get_params()

    def get_results_dir(self) -> Path:
        return Path(self._obj.get_results_dir())

    def get_logfiles(self) -> Path:
        return Path(self._obj.get_logfiles())


class Experiments:
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
        return getattr(self._obj, key)

    def __setitem__(self, key, value):
        setattr(self._obj, key, value)

    def __contains__(self, key):
        return hasattr(self._obj, key)

    def get(self, key, default=None):
        return getattr(self._obj, key, default)

    def get_all(self) -> list[str]:
        return self._obj.get_all()

    def get_path(self) -> Path:
        return self._path

    def get_name(self) -> str:
        return self._path.name


def get_experiment(experiments: SimpleNamespace, experiment: str) -> NS:
    obj = to_namespace(experiments[experiment])

    def get_apps(self) -> list[str]:
        return list(self.benchmarks)

    def get_params(self) -> list[str]:
        return list(self.params)

    def get_results(self) -> list[str]:
        return list(self.results)

    def get_results_dir(self) -> Path:
        return Path(self.results_dir)

    def get_logfiles(self) -> Path:
        return Path(self.logfiles)

    for name, fn in locals().items():
        if callable(fn) and name not in {"experiments", "obj"}:
            obj = add_method(obj, name, fn)

    return Experiment(obj, experiment)


def get(experiments: dict, path: Path=None) -> Experiments:
    obj = to_namespace(experiments)

    for name, fn in locals().items():
        if callable(fn) and name not in {"experiments", "obj"}:
            obj = add_method(obj, name, fn)
    return Experiments(obj, path)
