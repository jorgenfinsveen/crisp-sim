from . import *

class Config:
    def __init__(self, path: Path):
        self._path = path

    def _cast_value(self, v: str):
        try:
            return int(v)
        except ValueError:
            try:
                return float(v)
            except ValueError:
                return v

    def get_line(self, prefix: str, n=350):
        prefix = prefix.strip()
        if prefix == '' or prefix == '-':
            return None

        if not prefix.startswith('-'):
            prefix = f'-{prefix}'

        BYTES_TO_READ = int(250 * 1024 * 1024)
        count = 0
        with open(self._path, 'r', encoding='utf-8') as f:
            fsize = int(os.stat(self._path).st_size)
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

    def get_value(self, label, n=350):
        line = self.get_line(label, n)
        if not line or line == '':
            return None
        parts = line.split()
        if len(parts) == 1:
            return None
        return self._cast_value(" ".join(parts[1:]))

    def get_config(self) -> str:
        return self._path.resolve().parent.name

    def get_benchmark(self) -> str:
        return self._path.resolve().parent.parent.name

    def get_app(self) -> str:
        return self._path.resolve().parent.parent.parent.name

    def get_experiment(self) -> str:
        return self._path.resolve().parent.parent.parent.parent.name

    def get_path(self) -> Path:
        return self._path

    def get_name(self) -> str:
        return self._path.name


def get(path: Path) -> Config:
    return Config(path)
