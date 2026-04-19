#!/usr/bin/env python3
from __future__ import annotations

# Todo: Her kan vi lage kode for å lese csv- og visualizer-fil for å generere plots 
# Todo: Det er mulig vi er interessert i andre plots enn det som allerede finnes av plottescripts
# Todo: Det kan også være en idé å lage noe som trekker ut et gitt sett med verdier fra de forskjellige resultat-filene 
# Todo: ... og sammenligner hvilket som oppnådde best IPC, og deretter lagrer disse tallene + konfigurasjonen som ble brukt
# Todo: ... Det ville være gull verdt når vi gjør design-sweepinga!
from pathlib import Path
import os
import sys
import argparse
import utility.parser as ps



#Importing functions for plotting
from utility.plots.bar_chart import bar_chart
from utility.plots.stacked_bar_chart import stacked_bar_chart

PIPELINE_ROOT = Path(__file__).resolve().parent
PIPELINE_YAML = os.path.join(PIPELINE_ROOT, "setup", "pipeline.yaml")

pipeline = {}
experiment = {}

def parse_pipeline_config():
    global pipeline
    pipeline = ps.get_pipeline(PIPELINE_YAML)

def parse_experiment():
    global experiment
    experiment = ps.get_experiment(pipeline.experiment.name, pipeline.experiment.path)
    experiment.results_dir = Path(os.path.expandvars(experiment.results_dir))
    experiment.logfiles = Path(os.path.expandvars(experiment.logfiles))

def find_file(root: Path, filename: str) -> Path | None:
    for p in root.rglob(filename):
        if p.is_file():
            return p
    return None

def load_metric_metric() -> str:
    metric = pipeline.collect.metric
    if not metric: 
        raise SystemExit("pipeline.yaml missing experiment.name")
    return metric

def find_experiment_csvs(metric_metric: str) -> list[Path]:
    export_root = Path(os.path.join(experiment.results_dir, "export"))
    print(export_root)
    hits = list(export_root.rglob(f"*{metric_metric}*.csv"))
    return sorted([p for p in hits if p.is_file()])

def default_run():
    #metric_metric = load_metric_metric()
    global pipeline
    pipeline = ps.get_pipeline(PIPELINE_YAML)
    exp_name = pipeline.experiment.name
    print(exp_name)
    csvs = find_experiment_csvs(exp_name)
    #run_bar_charts_for_csvs(csvs)
    run_stacked_bar_charts_for_csvs(csvs)

def run_bar_charts_for_csvs(csv_paths: list[Path]):
    if not csv_paths:
        print("No matching CSV files found.")
        return

    print(f"Found {len(csv_paths)} CSV files. Generating bar charts...")

    for csv_path in csv_paths:
        try:
            bar_chart(str(csv_path))
            print(f"plotted: {csv_path}")
        except TypeError:
            bar_chart(str(csv_path))
            print(f"plotted: {csv_path}")

def run_stacked_bar_charts_for_csvs(csv_paths: list[Path]):
    if not csv_paths:
        print("No matching CSV files found.")
        return

    print(f"Found {len(csv_paths)} CSV files. Generating stacked bar charts...")

    for csv_path in csv_paths:
        try:
            stacked_bar_chart(str(csv_path))
            print(f"plotted: {csv_path}")
        except TypeError:
            stacked_bar_chart(str(csv_path))
            print(f"plotted: {csv_path}")


def menu():
    plots = {
        1: ("Bar chart", bar_chart),
    }

    print("Available plot types:")
    for k, (name, _) in plots.items():
        print(f"{k}: {name}")

    choice = input("Choose a plot type: ").strip()
    if not choice.isdigit() or int(choice) not in plots:
        print("Invalid choice")
        sys.exit(1)

    query = input("Experiment to match: ").strip()
    if not query:
        print("No input was provided.")
        sys.exit(1)
    if "/" in query or "\\" in query:
        print("Please provide only a filename or prefix (no paths).")
        sys.exit(1)

    if query.lower().endswith(".csv"):
        csv_path = find_file(PIPELINE_ROOT, query)
        if csv_path is None:
            print(f"Didn't find a file named: {query}")
            sys.exit(1)
        csvs = [csv_path]
    else:
        csvs = sorted([p for p in PIPELINE_ROOT.rglob(f"*{query}*.csv") if p.is_file()])
        if not csvs:
            print(f"No CSV files found matching: {query}")
            sys.exit(1)

    plot_name, plot_func = plots[int(choice)]

    print(f"Found {len(csvs)} CSV files. Generating {plot_name} charts...")
    for csv_path in csvs:
        plot_func(str(csv_path))
        print(f"Plotted: {csv_path}")

def main():
    parse_pipeline_config()
    parse_experiment()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-menu",
        action="store_true",
        help="launch menu"
    )
    args = parser.parse_args()
    if args.menu:
        menu()
    else:
        default_run()


if __name__ == "__main__":
    main()