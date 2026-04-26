from ..model import *
from types import SimpleNamespace, MethodType
from typing import Callable, Any, Iterable

class NS(SimpleNamespace):
    def __repr__(self) -> str:
        return repr(_repr_view(self))

    def __getitem__(self, key: str) -> Any:
        if not isinstance(key, str):
            raise TypeError(f"NS keys must be str, got {type(key).__name__}")
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise TypeError(f"NS keys must be str, got {type(key).__name__}")
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return isinstance(key, str) and hasattr(self, key)

    def __iter__(self):
        return iter(self.get_all())

    def keys(self) -> Iterable[str]:
        return (k for k, v in vars(self).items()
                if not k.startswith("_") and not callable(v))

    def items(self):
        return ((k, getattr(self, k)) for k in self.keys())

    def values(self):
        return (getattr(self, k) for k in self.keys())

def _repr_view(x: Any) -> Any:
    if isinstance(x, SimpleNamespace):
        return {
            k: _repr_view(v)
            for k, v in vars(x).items()
            if not k.startswith("_") and not callable(v)
        }
    if isinstance(x, dict):
        return {k: _repr_view(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_repr_view(v) for v in x]
    return x

def add_method(namespace: SimpleNamespace, name: str, func: Callable) -> SimpleNamespace:
    setattr(namespace, name, MethodType(func, namespace))
    return namespace

def to_namespace(obj: dict) -> SimpleNamespace:
    def get_all(self: SimpleNamespace) -> list:
        return [
            k for k, v in vars(self).items() if not k.startswith("_") and not callable(v)
        ]
    if isinstance(obj, dict):
        obj = NS(**{
            key: to_namespace(value)
            for key, value in obj.items()
        })
        return add_method(obj, "get_all", get_all)
    else:
        return obj


def to_dict(obj: SimpleNamespace) -> dict:
    if isinstance(obj, dict):
        return {
            k: to_dict(v)
            for k, v in obj.items()
            if not k.startswith("_") and not callable(v)
        }

    if isinstance(obj, SimpleNamespace):
        return {
            k: to_dict(v)
            for k, v in vars(obj).items()
            if not k.startswith("_") and not callable(v)
        }


    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]

    return obj
