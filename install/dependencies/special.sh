#!/usr/bin/env bash

# Prefer GCC/G++ 9 for this stack
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 90
update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 90

# Ensure modern Meson/Ninja (Mesa needs Meson >= 0.60)
apt-get purge -y meson || true
python3 -m pip install --no-cache-dir --upgrade pip
python3 -m pip install --no-cache-dir "meson>=1.2" "ninja>=1.11"
meson --version || true
ninja --version || true