# Installation guide

This repository is forked from https://github.com/JRPan/crisp-artifact and slightly adjusted in order to run on the IDUN cluster computer at the Norwegian University of Science and Technology.

## Setup on host

### Cloning
```bash
mkdir -p "$HOME/projects" && cd "$HOME/projects"
git clone https://github.com/jorgenfinsveen/crisp-sim.git crisp_framework
export CRISP_ROOT="$HOME/projects/crisp_framework"
export IDUN_SETUP="$CRISP_ROOT/.install/idun-setup"
```

### Creating necessary directories
```bash
mkdir -p "$HOME"/{opt,usr/local/bin,usr/local/cuda,.environments/python}
```

### Installing a Python environment
```bash
module load Python/3.13.5-GCCcore-14.3.0
python -m venv "$HOME/.environments/python/env"
cp -r "$IDUN_SETUP/pyenv" "$HOME"
chmod +x "$HOME/pyenv" && source "$HOME/pyenv"

pip install -r "$IDUN_SETUP/requirements.txt"
```

### Installing CUDA
```bash
export CUDA_VERSION="11.7"
export CUDA_DEST="$HOME/usr/local/cuda/cuda-$CUDA_VERSION"

module load "CUDA/$CUDA_VERSION.0"
cp -r "$CUDA_HOME" "$CUDA_DEST"
mv "$CUDA_DEST.0" "$CUDA_DEST"
ln -s "$CUDA_DEST/bin" "$HOME/usr/local/bin/cuda"
```

### Installing Embree3
```bash
export EMBREE_VERSION="3.13.5"
export EMBREE_INSTALL="$HOME/opt/embree3.tgz"
export EMBREE_VARS="$HOME/opt/embree-$EMBREE_VERSION.x86_64.linux/embree-vars.sh"
export EMBREE_URL="https://github.com/embree/embree/releases/download/v$EMBREE_VERSION/embree-$EMBREE_VERSION.x86_64.linux.tar.gz"

wget -O "$EMBREE_INSTALL" "$EMBREE_URL"
tar xzf "$EMBREE_INSTALL" && rm -f "$EMBREE_INSTALL"
source "$EMBREE_VARS"
```

### Installing VulkanSDK
```bash
export VULKAN_VERSION="1.3.296.0"
export VULKAN_DIR="$HOME/opt/vulkansdk"
export VULKAN_INSTALL="$VULKAN_DIR/vulkansdk.tar.xz"
export VULKAN_URL="https://sdk.lunarg.com/sdk/download/${VULKAN_VERSION}/linux/vulkansdk-linux-x86_64-${VULKAN_VERSION}.tar.xz?Human=true"

mkdir -p "$VULKAN_DIR" && cd "$VULKAN_DIR"
wget -O "$VULKAN_INSTALL" "$VULKAN_URL"
tar -xf "$VULKAN_INSTALL" && rm -f "$VULKAN_INSTALL"
ln -sfn "${VULKAN_VERSION}" current
```



## Building in container

### Prepare and build base-image
```bash
export CRISP_ROOT="$HOME/projects/crisp_framework"
export SRC="$CRISP_ROOT/.install/container/crisp-installer.def"
export IMG="$HOME/containers/crisp-installer"

mkdir -p "$HOME/containers" && cp "$SRC" "$IMG.def"
sed -i "s|/cluster/home/jorgfi|\$HOME|g" "$IMG.def"
apptainer build "$IMG.sif" "$IMG.def"
```

### Entering the container and mounting directories
```bash
apptainer shell \
	--nv \
	--writable-tmpfs \
    --bind $HOME/projects/crisp_framework:$HOME/projects/crisp_framework \
    --pwd $HOME/projects/crisp_framework \
    $HOME/containers/crisp-installer.sif
```

### Building CRISP
```bash
export CUDA_INSTALL_PATH="$HOME/usr/local/cuda/cuda-11.7"
export CUDA_HOME="$HOME/usr/local/cuda/cuda-11.7"
export VULKAN_SDK="$HOME/opt/vulkansdk/current/x86_64"
export EMBREE_ROOT="/opt/embree-$EMBREE_VERSION.x86_64.linux"
export PATH="$VULKAN_SDK/bin:$CUDA_HOME/bin:${PATH:+$PATH}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}$EMBREE_ROOT/lib:$CUDA_HOME/lib64:$VULKAN_SDK/lib"
export ROOT="$HOME/projects/crisp_framework"
export VULKAN_SIM="$ROOT/vulkan-sim"
export MESA_SIM="$ROOT/mesa-vulkan-sim"
exoprt MESA_ROOT="$ROOT/mesa-vulkan-sim"
export ACCEL_SIM="$ROOT/accel-sim-framework"

source "$VULKAN_SIM/setup_environment"
cd "$MESA_SIM" && rm -rf build

meson setup --prefix="${PWD}/lib" build \
	-Dgallium-drivers=iris,swrast,zink \
	-Dvulkan-drivers=intel,amd,swrast \
	-Dplatforms=x11,wayland
	
meson configure build \
	-Dbuildtype=debug \
	-Db_lundef=false
	
ninja -C build/ install

export VK_ICD_FILENAMES="$MESA_SIM/lib/share/vulkan/icd.d/lvp_icd.x86_64.json"

(cd "$VULKAN_SIM" && make -j)

ninja -C build/ install

(cd "$ACCEL_SIM/gpu-simulator" && rm -rf gpgpu-sim && source setup_environment.sh)
(source "$ACCEL_SIM/gpu-simulator/setup_environment.sh" && cd "$ACCEL_SIM" && make -j -C ./gpu-simulator)

exit
```


## Running the simulator

### Request interactive session
```bash
export HOST="stud.ntnu.no" # Change if applicable

salloc \
	--account=share-ie-idi \
	--cpus-per-task=2 \
	--partition=GPUQ \
	--mem=128G \
	--time=23:59:00 \
	--mail-type=ALL \
	--mail-user=$USER@$HOST
```

```bash
ssh [host]
```

### Final setup
```bash
cd "$HOME/projects/crisp_framework/accel-sim-framework"
source setup_environment.sh

./get_crisp_traces.sh

(cd util/graphics && python3 ./setup_concurrent.py)
```

### Running the simulator
```bash
run
```
