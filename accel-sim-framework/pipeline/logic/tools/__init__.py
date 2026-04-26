import os
import re
import csv
import yaml
import glob
import argparse
from pathlib import Path
from datetime import datetime
from ..model.config import Config, \
      get as config_get
from ..model.outfile import Outfile, \
      get as outfile_get
from ..model.traces import Traces, \
      get as traces_get
from ..model.simlog import SimulatorLogs, SimulatorLog, \
    new_sim_log_entry as sim_log_new_entry, \
    get as simlog_get, \
    new_log
from ..model.pipeline import Pipeline, \
    get as pipeline_get
from ..model.namespace import NS, \
    to_dict as namespace_to_dict
from ..model.experiment import Experiments, Experiment, \
    get as experiment_get, \
    get_experiment as extract_experiment
from typing import OrderedDict, defaultdict, Iterable, Optional

ROOT: Path = Path(os.path.expandvars('$ACCEL_SIM'))
PIPELINE_ROOT: Path = Path(os.path.join(ROOT, 'pipeline'))
PIPELINE_CONFIG: Path = os.path.join(PIPELINE_ROOT, 'settings', 'pipeline.yaml')

DASH_RE = re.compile(r"^-{5,}\s*,*")
CONFIG_LINE_RE = re.compile(r"^(?P<gpu>[^;]+);;(?P<kv>[^=]+)=(?P<val>.+)$")
KERNEL_ID_SUFFIX_RE = re.compile(r"-\d+$")
