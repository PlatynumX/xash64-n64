#!/usr/bin/env bash
set -euo pipefail

# Reproduce the exact upstream set reported by the r9 CI artifact. Advance these
# only after a successful frontier is understood and intentionally rebased.
XASH_SHA=${XASH_SHA:-ecda80fb9a29d45099a624344456eb3c7d01473d}
HLSDK_SHA=${HLSDK_SHA:-8c5b2846c2448e2b063f358f041d565dc0f076b1}
LIBDRAGON_SHA=${LIBDRAGON_SHA:-35f85a0797324a5ed0c723203e33ab3c1da94fdd}

mkdir -p upstream

fetch_pinned() {
    local url=$1 dir=$2 sha=$3
    if [[ ! -d "$dir/.git" ]]; then
        git clone --filter=blob:none --no-checkout "$url" "$dir"
    fi
    git -C "$dir" fetch --depth 1 origin "$sha"
    git -C "$dir" checkout --detach "$sha"
}

fetch_pinned https://github.com/FWGS/xash3d-fwgs.git upstream/xash3d-fwgs "$XASH_SHA"
git -C upstream/xash3d-fwgs submodule update --init --recursive --depth 1

fetch_pinned https://github.com/FWGS/hlsdk-portable.git upstream/hlsdk-portable "$HLSDK_SHA"
git -C upstream/hlsdk-portable submodule update --init --recursive --depth 1

fetch_pinned https://github.com/DragonMinded/libdragon.git upstream/libdragon "$LIBDRAGON_SHA"

python3 scripts/audit-xash-upstream.py upstream/xash3d-fwgs

printf 'xash3d-fwgs %s\n' "$(git -C upstream/xash3d-fwgs rev-parse HEAD)"
printf 'hlsdk-portable %s\n' "$(git -C upstream/hlsdk-portable rev-parse HEAD)"
printf 'libdragon %s\n' "$(git -C upstream/libdragon rev-parse HEAD)"
