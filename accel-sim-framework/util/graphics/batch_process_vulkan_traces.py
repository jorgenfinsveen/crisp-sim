#! /usr/bin/python3

import os
import argparse
import threading
import subprocess
from pathlib import Path

DIR_PATH: Path = Path(__file__).resolve().parent

parser = argparse.ArgumentParser()
parser.add_argument("--apps",  required=False, help="Comma-separated list of the names of the apps to parse.")
parser.add_argument("--src",   required=True,  help="Path to the source directory.")
parser.add_argument("--dest",  required=True, help="Path to the destination directory.")
args = parser.parse_args()

if not args.apps or args.apps == "*": apps = os.listdir(args.src)
else: apps = args.apps.split(",")

if not os.path.exists(args.dest):
    os.makedirs(args.dest)


def process_app(id: int, app: str):
    app = app if ".traceg" not in app else app[:-7]
    print(f"Thread {id}: started processing {args.src}/{app}.traceg.")

    if os.path.exists(f"{args.dest}/{app}"):
        print(f"Thread {id}: {args.dest}/{app} already exist. skipping")
        return

    result = subprocess.run(
        [f"{DIR_PATH}/process-vulkan-traces.py", "--app", app, "--src", args.src, "--dest", args.dest],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Thread {id}: error for {app}:\n{result.stderr}")
        if os.path.exists(f"{args.dest}/{app}"):
            subprocess.run(["rm", "-rf", f"{args.dest}/{app}"])
    else:
        print(f"Thread {id}: {app} processed at {args.dest}/{app}.")

threads = []

for idx, app in enumerate(apps):
    t = threading.Thread(target=process_app, args=(idx, app))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print("Processing complete:")
print(f"\t - Apps: {apps}")
print(f"\t - Dest: {args.dest}")
