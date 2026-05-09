#!/usr/bin/env bash

export CUSTOM_SETUP_ENVIRONMENT_WAS_RUN=

# Build and session management
export ROOT="$HOME/projects/crisp_framework"
export MESA_SIM="$ROOT/mesa-vulkan-sim"
export MESA_ROOT="$ROOT/mesa-vulkan-sim"
export VULKAN_SIM="$ROOT/vulkan-sim"
export ACCEL_SIM="$ROOT/accel-sim-framework"
export ACCELSIM_ROOT="$ACCEL_SIM"
export VK_ICD_FILENAMES="$MESA_SIM/lib/share/vulkan/icd.d/lvp_icd.x86_64.json"
export CC_VERSION="9.4.0"

# CUDA
export CUDA_VERSION="11.7"
export CUDA_HOME="$HOME/usr/local/cuda/cuda-$CUDA_VERSION"
export CUDA_INSTALL_PATH="$HOME/usr/local/cuda/cuda-$CUDA_VERSION"

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

# Accel-Sim git-hash
GIT_COMMIT=`git --git-dir=$ROOT/.git log --abbrev-commit -n 1 | head -1 | sed -re 's/commit (.*)/\1/'`
GIT_FILES_CHANGED=`git --git-dir=$ROOT/.git diff --numstat | wc | sed -re 's/^\s+([0-9]+).*/\1./'`
GIT_FILES_CHANGED+=`git --git-dir=$ROOT/.git diff --numstat --cached | wc | sed -re 's/^\s+([0-9]+).*/\1/'`
export ACCELSIM_COMMIT="$GIT_COMMIT-modified_$GIT_FILES_CHANGED"


set_gpgpusim_commit() {
    local l_git_dir="$ACCEL_SIM/gpu-simulator/gpgpu-sim/.git"
    GIT_COMMIT=`git --git-dir=$l_git_dir log --abbrev-commit -n 1 | head -1 | sed -re 's/commit (.*)/\1/'`
    GIT_FILES_CHANGED=`git --git-dir=$l_git_dir diff --numstat | wc | sed -re 's/^\s+([0-9]+).*/\1./'`
    GIT_FILES_CHANGED+=`git --git-dir=$l_git_dir diff --numstat --cached | wc | sed -re 's/^\s+([0-9]+).*/\1/'`
    GPGPUSIM_BUILD_STRING="gpgpu-sim_git-commit-$GIT_COMMIT-modified_$GIT_FILES_CHANGED"
    export GPGPUSIM_COMMIT="$GIT_COMMIT-modified_$GIT_FILES_CHANGED"
}



alias launch="(cd $ACCEL_SIM && python3 -m pipeline.launch)"
alias collect="(cd $ACCEL_SIM && python3 -m pipeline.collect)"

# Add all cached sim-runs from output/.cache/ into simulator_logs.yaml
# $1 - output directory (e.g. /cluster/projects/itea_lille-idi-epic-studenter/crisp/output)
cache_add() {
    (cd $ACCEL_SIM && python3 -m pipeline.logic.cache.add_data_from_cache --directory $1)
}

# Merge two instances from the same experiment
# $1 - experiment name
# $2 - first date
# $3 - second date
# $4 - result dir (e.g. /cluster/projects/itea_lille-idi-epic-studenter/crisp)
# $5 - new date (optional)
merge() {
    (cd $ACCEL_SIM && python3 -m pipeline.logic.tools.merge_experiment_dates --exp $1 --date_1 $2 --date_2 $3 --dir $4) #--new_date $5)
}

export CRISP_LOCAL="$ACCEL_SIM"

# Sources
source_all_environments() {
    GREEN="\e[32m"
    RED="\e[31m"
    RESET="\e[0m"

    echo "Initializing simulators:"
    source "$ROOT/vulkan-sim/setup_environment" >/dev/null 2>&1
    if [[ "$GPGPUSIM_SETUP_ENVIRONMENT_WAS_RUN" == "1" ]]; then
        echo -e "   [vulkan-sim]: ${GREEN}Ready${RESET}"
    else
        echo -e "   [vulkan-sim]: ${RED}Error${RESET}"
    fi

    source "$ACCEL_SIM/gpu-simulator/setup_environment.sh" >/dev/null 2>&1
    if [[ "$ACCELSIM_SETUP_ENVIRONMENT_WAS_RUN" == "1" ]]; then
        echo -e "   [accel-sim]:  ${GREEN}Ready${RESET}"
    else
        echo -e "   [accel-sim]:  ${RED}Error${RESET}"
    fi

    source "$ACCEL_SIM/gpu-simulator/gpgpu-sim/setup_environment" >/dev/null 2>&1
    if [[ "$GPGPUSIM_SETUP_ENVIRONMENT_WAS_RUN" == "1" ]]; then
        echo -e "   [gpgpu-sim]:  ${GREEN}Ready${RESET}"
    else
        echo -e "   [gpgpu-sim]:  ${RED}Error${RESET}"
    fi
}

# Creates symlink to dir with the .so-files for CUDA within the gcc-x.x dir
ensure_gcc_symlink_in_dir() {
    local t_path="$1"

    shopt -s nullglob
    local dirs=("$t_path"/gcc-*/)
    shopt -u nullglob

    if [[ ${#dirs[@]} -eq 0 ]]; then
        echo "Error: There is no gcc-x.x directory in $t_path" >&2
        return 1
    fi

    local target="${dirs[0]%/}"
    local link="$t_path/gcc-"

    [[ -e "$link" ]] && return 0
    ln -s "$target" "$link"
}

# Resolves dir-mismatch in gpgpu-sim/lib and Vulkan-sim/lib
assert_gcc_symlink() {
    ensure_gcc_symlink_in_dir "$ACCEL_SIM/gpu-simulator/gpgpu-sim/lib" || return 1
    ensure_gcc_symlink_in_dir "$ROOT/vulkan-sim/lib" || return 1
}


# Setup simulator
set_sim() {
	cd $ACCEL_SIM
    source $HOME/pyenv
	assert_gcc_symlink
	source_all_environments
	./run.sh
}

# Run simulator in detached mode
run() {
	export -f set_sim
	export -f assert_gcc_symlink
	export -f source_all_environments

	rm -rf "$ACCEL_SIM/logs" && mkdir -p "$ACCEL_SIM/logs"

	nohup bash -c 'set_sim' > "$ACCEL_SIM/logs/out.log" 2> "$ACCEL_SIM/logs/err.log" &
	echo "Simulator started with PID $!"
}

# Python environment
source $HOME/pyenv
assert_gcc_symlink
source_all_environments
set_gpgpusim_commit


export CUSTOM_SETUP_ENVIRONMENT_WAS_RUN=1
