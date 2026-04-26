from __future__ import annotations
import os
import subprocess
from pathlib import Path
from .logic.tools.parser import *
from .logic.view.bar_chart import *
from .logic.view.stacked_bar_chart import *

ROOT: Path                  = os.path.expandvars('$ACCEL_SIM')
PIPELINE_ROOT: Path         = os.path.join(ROOT, 'pipeline')
PIPELINE_CONFIG: Path       = os.path.join(PIPELINE_ROOT, 'settings', 'pipeline.yaml')
CONFIGURATIONS_ROOT: Path   = os.path.join(PIPELINE_ROOT, 'configs')
ENVIRONMENT: Path           = os.path.join(ROOT, 'setup_environment.sh')

JOB_LAUNCHING_DIR: Path         = os.path.join(ROOT, 'util', 'job_launching')
GET_STATS_SCRIPT: Path          = os.path.join(JOB_LAUNCHING_DIR, 'get_stats.py')
RUN_SIMULATIONS_SCRIPT: Path    = os.path.join(JOB_LAUNCHING_DIR, 'run_simulations.py')
STANDARD_CONFIGURATIONS: Path   = os.path.join(JOB_LAUNCHING_DIR, 'configs', 'define-standard-cfgs.yml')

PIPELINE_LOGIC_DIR: Path      = os.path.join(PIPELINE_ROOT, 'logic')
CACHE_LAUNCH_DATA_SCRIPT: Path  = os.path.join(PIPELINE_LOGIC_DIR, 'cache', 'cache_launch_data.py')
ADD_FROM_CACHE_SCRIPT: Path  = os.path.join(PIPELINE_LOGIC_DIR, 'cache', 'add_data_from_cache.py')

CALL_COLLECT_CSV_SCRIPT: str = ['python3', '-m', 'logic.tools.collect-csv']

SHEBANG: str = '#!/usr/bin/env bash\n'
PIPEFAIL: str = 'set -euo pipefail\n'
LAUNCH_DATE: str = f'launch_date=$(date +"%Y_%m_%d__%H_%M")\n\n'
