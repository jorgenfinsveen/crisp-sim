from . import *

class Outfile:
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

    def get_line(self, prefix: str, ignore: str=None, n=350):
        prefix = prefix.strip()
        if prefix == '' or prefix == '-':
            return None
        count = 0
        with open(self._path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line:
                    continue
                count += 1
                if count >= n:
                    return None
                if prefix in line:
                    if ignore == None or ignore.strip() == "":
                        return line.strip()
                    if ignore.strip().lower() not in line.lower():
                        return line.strip()
            return None

    def get_value(self, label, ignore: str=None, n=350):
        line = self.get_line(label, ignore, n)
        if not line or line == '':
            return None
        parts = line.split()
        if len(parts) == 1:
            return None
        return self._cast_value(" ".join(parts[1:]))

    def get_config(self) -> str:
        return self._path.resolve().parent.name

    def get_app(self) -> str:
        return self._path.resolve().parent.parent.name

    def get_benchmark(self) -> str:
        return self._path.resolve().parent.parent.parent.name

    def get_experiment(self) -> str:
        return self._path.resolve().parent.parent.parent.parent.name

    def get_node(self):
        with open(self._path, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                count += 1
                if count >= 100:
                    return None
                if line.startswith('node'):
                    return line.strip().split(':')[1]
            return None

    def _search_in_string(self, s: str, start: str, end = None) -> str:
        i = s.find(start)
        if i == -1:
            return ""
        start_idx = i + len(start)
        if end is None:
            return s[start_idx:]
        j = s.find(end, start_idx)
        return s[start_idx:j] if j != -1 else ""

    def get_commit_hashes(self):
        labels = (
            ('accelsim_commit', 'accelsim-commit-'),
            ('gpgpusim_commit', 'gpgpu-sim_git-commit-')
        )
        ignore = ('Skipping', 'doing', 'node')
        end = ']'
        hashes = {}
        for label in labels:
            hashes[label[0]] = ''
        with open(self._path, 'r', encoding='utf-8') as f:
            count = 0
            filled_labels = 0
            for line in f:
                count += 1
                if count >= 100:
                    break
                for i in ignore:
                    if line.startswith(ignore):
                        continue
                for label in labels:
                    if len(labels) == filled_labels:
                        return hashes
                    if hashes[label[0]] == '':
                        res = self._search_in_string(line, label[1], end)
                        if res != '':
                            hashes[label[0]] = res
                            filled_labels += 1
        return hashes

    def get_path(self) -> Path:
        return self._path

    def get_name(self) -> str:
        return self._path.name


def get(path: Path) -> Outfile:
    return Outfile(path)
