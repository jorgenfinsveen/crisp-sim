# Installation guide

This repository is forked from https://github.com/JRPan/crisp-artifact and slightly adjusted in order to run on the IDUN cluster computer at the Norwegian University of Science and Technology.

## Setup on host

### Cloning
```bash
mkdir -p "$HOME/projects"
git clone https://github.com/jorgenfinsveen/crisp-sim.git crisp_framework
```

### Creating necessary directories
```bash
mkdir -p "$HOME/usr/local"
mkdir -p "$HOME/opt"
mkdir -p "$HOME/.environment/python"
```

### Installing a Python environment
```bash
module load Python/3.13.5-GCCcore-14.3.0
python -m venv "$HOME/.environments/python/env"
cp "$HOME/projects/.install/idun-setup/pyenv" $HOME
chmod +x "$HOME/pyenv"
source "$HOME/pyenv"

pip install -r "$HOME/projects/.install/idun-setup/requirements.txt"
```

### Installing CUDA
```bash
export CUDA_VERSION="11.7.0"

module load "CUDA/$CUDA_VERSION"
cp -r $(which nvcc) "$HOME/usr/local/cuda-11.7"
ln -s "$HOME/usr/local/cuda-11.7" "$HOME/usr/local/cuda-$CUDA_VERSION"
```

### Installing Embree3
```bash
export EMBREE_VERSION="3.13.5"
cd "$HOME/opt"
wget -O embree3.tgz https://github.com/embree/embree/releases/download/v$EMBREE_VERSION/embree-$EMBREE_VERSION.x86_64.linux.tar.gz
tar xzf embree3.tgz && rm -f embree3.tgz
. /opt/embree-$EMBREE_VERSION.x86_64.linux/embree-vars.sh
```

### Installing VulkanSDK
```bash
export VULKAN_VERSION="1.3.296.0"
mkdir -p "$HOME/opt/vulkansdk"
cd "$HOME/opt/vulkansdk"
wget -O vulkansdk.tar.xz "https://sdk.lunarg.com/sdk/download/${VULKAN_VERSION}/linux/vulkansdk-linux-x86_64-${VULKAN_VERSION}.tar.xz?Human=true"
tar -xf vulkansdk.tar.xz && rm -f vulkansdk.tar.xz
ln -sfn "${VULKAN_VERSION}" current
```



## Building in container

### Prepare and build base-image
```bash
mkdir -p "$HOME/containers"
img="$HOME/containers/crisp-installer.def"
mv $HOME/projects/crisp_framework/.install/crisp-installer.def $img
sed -i "s|/cluster/home/jorgfi|\$HOME|g" $img
apptainer build $HOME/containers/crisp-installer.sif $img
```

### Entering the container and mounting directories
```bash
apptainer shell --nv --writable-tmpfs \
    --bind $HOME/projects/crisp_framework:$HOME/projects/crisp_framework \
    --pwd $HOME/projects/crisp_framework \
    $HOME/containers/crisp-installer.sif
```

### Building CRISP
```bash
export CUDA_INSTALL_PATH="$HOME/usr/local/cuda-11.7"
source $ROOT/vulkan-sim/setup_environment
cd $ROOT/mesa-vulkan-sim
rm -rf build

meson setup --prefix="${PWD}/lib" build \
	-Dgallium-drivers=iris,swrast,zink \
	-Dvulkan-drivers=intel,amd,swrast \
	-Dplatforms=x11,wayland
	
meson configure build \
	-Dbuildtype=debug \
	-Db_lundef=false
	
meson configure build

ninja -C build/ install

export VK_ICD_FILENAMES="$ROOT/mesa-vulkan-sim/lib/share/vulkan/icd.d/lvp_icd.x86_64.json"

(cd $ROOT/vulkan-sim && make -j)

ninja -C build/ install

cd $HOME/accel-sim-framework
source gpu_simulator/setup_environment
make -j -C ./gpu-simulator
exit
```


## Running the simulator

### Request interactive session
```bash
salloc --account=share-ie-idi \
	--cpus-per-task=1 \
	--partition=GPUQ \
	--mem=128G \
	--time=15:30:00 \
	--mail-type=ALL \
	--mail-user=$USER@stud.ntnu.no # Use other host if applicable.
```

```bash
ssh $USER@[host]
```

### Final setup
```bash
cd $HOME/projects/crisp_framework/accel-sim-framework
source env_setup.sh

./get_crisp_traces.sh

(cd util/graphics && python3 ./setup_concurrent.py)
```

### Running the simulator
```bash
run
```
