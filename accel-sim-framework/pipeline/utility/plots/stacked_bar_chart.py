#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from utility.kernel_handler import KernelHandler
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import statistics
import re


def extract_number(value) -> str:
    m = re.search(r"\d+", str(value))
    return m.group(0) if m else str(value)


def get_gpu_name(csv_path: Path) -> str:
    return csv_path.parent.name


def build_kernel_handler_from_df(df: pd.DataFrame) -> KernelHandler:
    kernel_names = []
    for col_name in df.columns[1:]:
        if col_name == "AVG":
            continue
        parts = col_name.split("/")
        if len(parts) > 2:
            kernel_names.append(parts[2])
    return KernelHandler(kernel_names)


def compute_render_compute_for_row(
    df: pd.DataFrame, row_idx: int, kernel_handler: KernelHandler
) -> tuple[float, float]:
    render_vals: list[float] = []
    compute_vals: list[float] = []

    for col_name in df.columns[1:]:
        if col_name == "AVG":
            continue

        parts = col_name.split("/")
        if len(parts) < 3:
            continue

        kernel_name = parts[2]
        val = df.loc[row_idx, col_name]

        if pd.isna(val):
            continue

        if kernel_handler.is_render_kernel(kernel_name):
            render_vals.append(float(val))
        else:
            compute_vals.append(float(val))

    render_avg = statistics.mean(render_vals) if render_vals else 0.0
    compute_avg = statistics.mean(compute_vals) if compute_vals else 0.0
    return render_avg, compute_avg


def staked_bar_chart(csv_path: str) -> None:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)

    kernel_handler = build_kernel_handler_from_df(df)

    configs = df.iloc[:, 0].tolist()
    x_labels = [extract_number(c) for c in configs]
    x_pos = np.arange(len(x_labels))

    y_render: list[float] = []
    y_compute: list[float] = []

    for row_idx in range(len(configs)):
        r, c = compute_render_compute_for_row(df, row_idx, kernel_handler)
        y_render.append(r)
        y_compute.append(c)

    gpu_name = get_gpu_name(csv_path)

    plt.figure(figsize=(max(10, len(x_labels) * 0.8), 6))
    plt.bar(x_pos, y_render, label="render")
    plt.bar(x_pos, y_compute, bottom=y_render, label="compute")
    plt.xticks(x_pos, x_labels)
    plt.ylabel("Average Time")
    plt.grid(True)
    plt.legend()
    plt.title(f"Average render and compute time for {gpu_name}")
    plt.tight_layout()
    out_path = csv_path.with_suffix("").parent / f"{csv_path.stem}_stacked_bar_chart.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()