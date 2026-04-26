#!/usr/bin/env python3

from . import *


def _label(name: str) -> str:
    return name.replace("_", " ").strip().title()


def bar_chart(csv_path: str) -> None:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)

    if df.shape[1] < 2:
        raise ValueError(
            "CSV must have at least 2 columns: first=config, remaining=benchmarks"
        )

    config_col = df.columns[0]
    metric_row = csv_path.stem
    metric_label = metric_row #_label(metric_row)

    df_long = df.melt(
        id_vars=config_col,
        var_name="benchmark",
        value_name=metric_label
    )

    benchmarks = df_long["benchmark"].unique()
    configs = df_long[config_col].unique()

    num_benchmarks = len(benchmarks)
    num_configs = len(configs)
    x = range(num_benchmarks)
    width = 0.8 / max(1, num_configs)

    plot_width  = 5 * num_configs
    plot_height = plot_width // 2

    plt.figure(figsize=(plot_width, plot_height))

    for i, cfg in enumerate(configs):
        vals = df_long[df_long[config_col] == cfg][metric_label].to_list()
        plt.bar([p + i * width for p in x], vals, width, label=str(cfg))

    mid = (num_configs - 1) * width / 2
    plt.xticks([p + mid for p in x], benchmarks, rotation=30, ha="right")

    plt.ylabel(metric_label)
    plt.title(f"{metric_label} for each benchmark")
    plt.legend(title=config_col)
    plt.tight_layout()
    plt.grid(True)
    out_file = csv_path.with_suffix("")
    out_file = out_file.parent / f"{out_file.name}_by_benchmark.png"
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
