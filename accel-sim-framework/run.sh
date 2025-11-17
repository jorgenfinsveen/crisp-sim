#!/usr/bin/env bash

run_simulations="$ACCEL_SIM/util/job_launching/run_simulations.py"
LAUNCHER="local"

$run_simulations \
	--launcher $LAUNCHER \
	-B crisp-artifact:render_passes_2k_lod0 \
	-C ORIN-SASS-concurrent-fg-VISUAL,RTX3070-SASS-concurrent-fg-VISUAL \
	-T ./hw_run/traces/vulkan/ \ 
	-N run-20240723-1728-render_passes_2k_lod0

$run_simulations \
	--launcher $LAUNCHER \
	-B crisp-artifact:render_passes_2k \
	-C ORIN-SASS-concurrent-fg-VISUAL,RTX3070-SASS-concurrent-fg-VISUAL \
	-T ./hw_run/traces/vulkan/ \
	-N run-20240723-1728-render_passes_2k
