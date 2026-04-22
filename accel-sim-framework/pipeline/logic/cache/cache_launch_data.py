#!/usr/bin/env python3

import os
import json
import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument("--date", required=False, help="")
argparser.add_argument("--experiment", required=False, help="")
argparser.add_argument("--accelsim_commit", required=False, help="")
argparser.add_argument("--gpgpusim_commit", required=False, help="")
argparser.add_argument("--directory", required=False, help="")
argparser.add_argument("--benchmarks", required=False, help="")
argparser.add_argument("--parameters", required=False, help="")
argparser.add_argument("--configurations", required=False, help="")
argparser.add_argument("--result_variables", required=False, help="")
args = argparser.parse_args()
args.directory = os.path.expandvars(args.directory)


def main():
    cache = {
        "experiment": args.experiment,
        "accelsim_commit": args.accelsim_commit,
        "gpgpusim_commit": args.gpgpusim_commit,
        "directory": args.directory,
        "benchmarks": args.benchmarks.split(","),
        "parameters": args.parameters.split(","),
        "configurations": args.configurations.split(","),
        "result_variables": args.result_variables.split(",")
    }

    cache_dir = os.path.join(args.directory, ".cache/")
    cache_file = os.path.join(cache_dir, f"{args.date}.json")
    os.system(f"mkdir -p {cache_dir}")

    if os.path.exists(cache_file):
        os.system(f"rm {cache_file}")

    with open(file=cache_file, mode="w", encoding="utf-8") as f:
        json.dump(cache, f)



if __name__ == "__main__":
    main()
