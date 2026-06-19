#!/usr/bin/env python3

import argparse
import csv
import glob
import os
import re
import sys
import yaml
from pathlib import Path


ID_FIELDS = ['kernel_name', 'kernel_launch_uid']
RUNTIME_FIELDS = ['kernel_start_cycle', 'kernel_end_cycle', 'kernel_launch_latency']

'''
Utregning:
------------------
Vi må ikke bruke gcstack_launch latency for den er jevnt fordelt utover SMene
Den burde vi faktisk vurdere å oppdatere slik at den gir faktisk oppstart

Vi starter med kernel_end_cycle som utgangspunkt
Deretter tar vi å trekker fra gcstack_finished (muligens last_ins også) for å finne én SMs relative slutt
For å finne faktisk start så må vi trekke fra alle andre gcstack-verdier bortsett fra finished og launch_latency

'''
