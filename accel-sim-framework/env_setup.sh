#!/usr/bin/env bash

# Build and session management
export ROOT="$HOME/projects/crisp_framework"
export MESA_SIM="$ROOT/mesa-vulkan-sim"
export ACCEL_SIM="$ROOT/accel-sim-framework"
export ACCELSIM_ROOT="$ACCEL_SIM"
export VK_ICD_FILENAMES="$MESA_SIM/lib/share/vulkan/icd.d/lvp_icd.x86_64.json"
export CC_VERSION="9.4.0"

# CUDA
export CUDA_VERSION="11.7"
export CUDA_HOME="$HOME/usr/local/cuda-$CUDA_VERSION"
export CUDA_INSTALL_PATH="$HOME/usr/local/cuda-$CUDA_VERSION"

# Embree
export EMBREE_VERSION="3.13.5"
export EMBREE_ROOT="$HOME/opt/embree-$EMBREE_VERSION.x86_64.linux"
export EMBREE_DIR="$EMBREE_ROOT"
export embree_DIR="$EMBREE_ROOT/lib/cmake/embree-$EMBREE_VERSION"

# VulkanSDK
export VULKAN_VERSION="1.3.296.0"
export VULKAN_SDK="$HOME/opt/vulkansdk/current/x86_64"

# Paths
export PATH="$VULKAN_SDK/bin:$CUDA_HOME/bin:${PATH:+$PATH}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}$EMBREE_ROOT/lib:$CUDA_HOME/lib64:$VULKAN_SDK/lib"

# Python environment
source $HOME/pyenv


# Sources
setup_env() {
    GREEN="\e[32m"
    RED="\e[31m"
    RESET="\e[0m"

    if source "$ROOT/vulkan-sim/setup_environment" >/dev/null 2>&1; then
        echo -e "[vulkan-sim] Source: ${GREEN}Success${RESET}"
    else
        echo -e "[vulkan-sim] Source: ${RED}Failed${RESET}"
    fi

    if source "$ACCEL_SIM/gpu-simulator/setup_environment.sh" >/dev/null 2>&1; then
        echo -e "[accel-sim] Source: ${GREEN}Success${RESET}"
    else
        echo -e "[accel-sim] Source: ${RED}Failed${RESET}"
    fi
}

# Resolves dir-mismatch in GPGPU-Sim/lib
assert_gcc_symlink() {
    t_path="$ACCEL_SIM/gpu-simulator/gpgpu-sim/lib"

    shopt -s nullglob
    dirs=("$t_path"/gcc-*/)
    shopt -u nullglob

    if [[ ${#dirs[@]} -eq 0 ]]; then
        echo "Error: There is no gcc-x.x directory in $t_path" >&2
        return 1
    fi

    target="${dirs[0]%/}"
    link="$t_path/gcc-"

    if [[ -L "$link" ]]; then
        return 0
    fi

    if [[ -e "$link" ]]; then
        return 0
    fi

    ln -s "$target" "$link"
}

# Setup simulator
set_sim() {
	source $HOME/pyenv
	cd $ACCEL_SIM
	assert_gcc_symlink
	setup_env
	(cd util/graphics && python3 ./setup_concurrent.py)
	./run.sh
}

# Run simulator in detached mode
run() {
	export -f setup_env
	export -f set_sim
	export -f assert_gcc_symlink

	rm -rf "$ACCEL_SIM/logs" && mkdir -p "$ACCEL_SIM/logs"
	
	nohup bash -c 'set_sim' > "$ACCEL_SIM/logs/out.log" 2> "$ACCEL_SIM/logs/err.log" &
	echo "Simulator started with PID $!"
}
