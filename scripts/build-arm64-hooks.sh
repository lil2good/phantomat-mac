#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
deps="$project_dir/.build/deps"

checkout() {
  local name=$1 url=$2 revision=$3
  if [[ ! -d "$deps/$name/.git" ]]; then
    git init -q "$deps/$name"
    git -C "$deps/$name" remote add origin "$url"
    git -C "$deps/$name" fetch --depth 1 origin "$revision"
    git -C "$deps/$name" checkout --detach FETCH_HEAD
  fi
  [[ $(git -C "$deps/$name" rev-parse HEAD) == "$revision" ]] || {
    echo "Unexpected $name revision in $deps/$name" >&2
    exit 1
  }
}

checkout funchook https://github.com/kubo/funchook.git b4991704add411ecbc492dae020f375124d51f45
checkout capstone https://github.com/capstone-engine/capstone.git 097c04d9413c59a58b00d4d1c8d5dc0ac158ffaa
cmake -S "$deps/funchook" -B "$deps/funchook/build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DFUNCHOOK_BUILD_SHARED=OFF -DFUNCHOOK_BUILD_TESTS=ON \
  -DFETCHCONTENT_SOURCE_DIR_CAPSTONE="$deps/capstone" \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build "$deps/funchook/build" -j "${CMAKE_BUILD_PARALLEL_LEVEL:-4}"
ctest --test-dir "$deps/funchook/build" --output-on-failure
