from . import *

class Traces:
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

    def get_all(self: SimpleNamespace) -> list[str]:
        return self._obj.get_all()

    def get_path(self, app: str, expandvars: bool=True) -> Path:
        return self._obj.get_path(app, expandvars)

    def get_path(self) -> Path:
        return self._path

    def get_name(self) -> str:
        return self._path.name


def get(traces: dict, path: Path=None) -> Traces:
    obj = to_namespace(traces)

    def get_path(self, app: str, expandvars: bool=True) -> Path:
        path = getattr(self, app)
        if expandvars:
            path = os.path.expandvars(path)
        return path

    for name, fn in locals().items():
        if callable(fn) and name not in {"traces", "obj"}:
            obj = add_method(obj, name, fn)

    return Traces(obj, path)
