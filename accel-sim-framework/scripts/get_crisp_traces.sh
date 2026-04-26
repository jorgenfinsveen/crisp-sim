#!/usr/bin/env bash
./clean_hw_run_traces.sh
mkdir -p hw_run/traces/vulkan

if [[ ! -d spl_vio ]]; then
	curl https://zenodo.org/records/13287587/files/spl_vio.tar.gz?download=1 --output spl_vio.tar.gz
	tar --no-same-owner --no-same-permissions -xvf spl_vio.tar.gz
fi

cp -r spl_vio/* hw_run/traces/vulkan