#!/usr/bin/env bash
mkdir -p hw_run/traces/vulkan

for d in klt_tracker render_passes_2k render_passes_2k_lod0 \
         vpi_sample_03_harris_corners vpi_sample_11_fisheye \
         vpi_sample_12_optflow_lk vpi_sample_12_optflow_lk_refined
do
  rm -rf "hw_run/traces/vulkan/$d"
done