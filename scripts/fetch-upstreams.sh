#!/usr/bin/env bash
set -euo pipefail

mkdir -p upstream

if [[ ! -d upstream/xash3d-fwgs/.git ]]; then
    git clone --recursive https://github.com/FWGS/xash3d-fwgs.git upstream/xash3d-fwgs
else
    git -C upstream/xash3d-fwgs fetch --all --prune
    git -C upstream/xash3d-fwgs submodule update --init --recursive
fi

if [[ ! -d upstream/hlsdk-portable/.git ]]; then
    git clone --recursive https://github.com/FWGS/hlsdk-portable.git upstream/hlsdk-portable
else
    git -C upstream/hlsdk-portable fetch --all --prune
    git -C upstream/hlsdk-portable submodule update --init --recursive
fi

python3 scripts/audit-xash-upstream.py upstream/xash3d-fwgs

git -C upstream/xash3d-fwgs rev-parse HEAD
git -C upstream/hlsdk-portable rev-parse HEAD
