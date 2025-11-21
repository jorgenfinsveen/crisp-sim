#!/usr/bin/env bash

install_dependencies() {
	local DEPENDENCIES_LIST="$1/packages.txt"
	
	apt-get update
	apt-get install -y $(cat $DEPENDENCIES_LIST)

	# Prefer GCC/G++ 9 for this stack
	update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 90
	update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 90

	# Ensure modern Meson/Ninja (Mesa needs Meson >= 0.60)
	apt-get purge -y meson || true
	python3 -m pip install --no-cache-dir --upgrade pip
	python3 -m pip install --no-cache-dir "meson>=1.2" "ninja>=1.11"
	meson --version || true
	ninja --version || true
}

install_cuda() {
   	cd /tmp
    wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
	mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
	apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub
	add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /"
	apt-get update
	apt-get -y install cuda
}

install_embree() {
	cd /opt
   	wget -O embree3.tgz https://github.com/embree/embree/releases/download/v$EMBREE_VERSION/embree-$EMBREE_VERSION.x86_64.linux.tar.gz
    tar xzf embree3.tgz && rm -f embree3.tgz

    # Auto-source Embree env for interactive shells
    cat >/etc/profile.d/embree.sh <<'EOS'
    if [ -f /opt/embree-$EMBREE_VERSION.x86_64.linux/embree-vars.sh ]; then
        . /opt/embree-$EMBREE_VERSION.x86_64.linux/embree-vars.sh
    fi
EOS
}

install_vulkan() {
	mkdir -p /opt/vulkansdk
   	cd /opt/vulkansdk
   	wget -O vulkansdk.tar.xz "https://sdk.lunarg.com/sdk/download/${VULKAN_VERSION}/linux/vulkansdk-linux-x86_64-${VULKAN_VERSION}.tar.xz?Human=true"
   	tar -xf vulkansdk.tar.xz && rm -f vulkansdk.tar.xz
   	ln -sfn "${VULKAN_VERSION}" current
}

install_software() {
	source "$1/software.sh"

    GREEN="\e[32m"
    RED="\e[31m"
    NC="\e[0m"
	
    echo "Starting installation of SDKs. This may take a while..."
	echo -ne "Installing Embree ($EMBREE_VERSION): "; install_embree > /dev/null 2>&1 && echo -e "${GREEN}SUCCESS${NC}" || echo -e "${RED}FAILED${NC}"
	echo -ne "Installing VulkanSDK ($VULKAN_VERSION): "; install_vulkan > /dev/null 2>&1 && echo -e "${GREEN}SUCCESS${NC}" || echo -e "${RED}FAILED${NC}"
	echo -ne "Installing CUDA ($CUDA_VERSION): "; install_cuda > /dev/null 2>&1 && echo -e "${GREEN}SUCCESS${NC}" || echo -e "${RED}FAILED${NC}"
	echo -e "\n"
}