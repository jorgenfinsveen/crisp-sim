#!/usr/bin/env bash

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



build_vulkan() {
    source "$VULKAN_SIM/setup_environment"
    cd "$MESA_SIM" && rm -rf build

    (
        cd "$MESA_SIM"

        meson setup --prefix="${PWD}/lib" build \
            -Dgallium-drivers=iris,swrast,zink \
            -Dvulkan-drivers=intel,amd,swrast \
            -Dplatforms=x11,wayland

        meson configure build \
	        -Dbuildtype=debug \
	        -Db_lundef=false

        ninja -C build/ install
    )

    (cd "$VULKAN_SIM" && make -j)

    ninja -C build/ install
    cd "$ROOT"
}

build_accelsim() {
    cd "$ACCEL_SIM/gpu-simulator"
    source setup_environment.sh

    source "$ACCEL_SIM/gpu-simulator/setup_environment.sh"
    cd "$ACCEL_SIM"
    make clean
    #make -j -C ./gpu-simulator -n 2>&1 | grep "^g++" | head -5
    make -j -C ./gpu-simulator
    cd "$ROOT"
}


build_accelsim_hard() {
   cd "$ACCEL_SIM/gpu-simulator/gpgpu-sim"
   rm -rf "build" "lib"
   cd "$ACCEL_SIM/gpu-simulator"
   rm -rf "build" "bin"
   build_accelsim
   cd "$ROOT"
}

build_gpgpusim_hard() {
    cd "$ACCEL_SIM/gpu-simulator/gpgpu-sim"
    rm -rf "build" "lib"
    cd "$ACCEL_SIM/gpu-simulator"
    source "setup_environment.sh"
    cd "$ACCEL_SIM"
    make clean
    make -j -C ./gpu-simulator gpgpu-sim
    cd "$ROOT"
}

build_all() {
    build_vulkan
    build_accelsim
    cd "$ROOT"
}

container() {
    apptainer shell \
        --nv \
        --writable-tmpfs \
        --bind $HOME/projects/crisp_framework:$HOME/projects/crisp_framework \
        --pwd $HOME/projects/crisp_framework \
        $HOME/containers/crisp-installer.sif
}

build() {
    local warn_level="error_only"

    if [[ "$1" == "warn" ]]; then
        warn_level="warn"    
    fi

    apptainer exec \
        --nv \
        --writable-tmpfs \
        --bind $HOME/projects/crisp_framework:$HOME/projects/crisp_framework \
        --pwd $HOME/projects/crisp_framework \
        $HOME/containers/crisp-installer.sif \
        bash -c "source build_env.sh && export MAKE_LOG_LEVEL=$warn_level && build_accelsim_hard"
}

build2() {
    local warn_level="error_only"

    if [[ "$1" == "warn" ]]; then
        warn_level="warn"    
    fi

    apptainer exec \
        --nv \
        --writable-tmpfs \
        --bind $HOME/projects/crisp_framework:$HOME/projects/crisp_framework \
        --pwd $HOME/projects/crisp_framework \
        $HOME/containers/crisp-installer.sif \
        bash -c "source build_env.sh && export MAKE_LOG_LEVEL=$warn_level && build_gpgpusim_hard"
}
