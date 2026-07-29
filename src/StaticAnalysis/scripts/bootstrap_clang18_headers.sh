#!/usr/bin/env bash
set -euo pipefail

readonly package_version='1:18.1.8~++20240731024944+3b5b5c1ec4a3-1~exp1~20240731145000.144'
readonly package_sha256='c1e3eb5c7c930062457f91eb10542a9d6a3eecc39cc198bc4facb712cc0927d0'

if [[ $# -ne 1 ]]; then
  echo "usage: $0 ABSOLUTE_EXTRACTION_ROOT" >&2
  exit 2
fi

destination=$1
if [[ ${destination:0:1} != / ]]; then
  echo 'extraction root must be absolute' >&2
  exit 2
fi
header_root="${destination}/usr/lib/llvm-18/include"
if [[ -f "${header_root}/clang/AST/AST.h" ]]; then
  echo "PASS existing_clang_include=${header_root}"
  exit 0
fi
if [[ -e ${destination} ]]; then
  echo "refusing to overwrite non-matching destination: ${destination}" >&2
  exit 2
fi

temporary=$(mktemp -d /tmp/rift-clang18-dev.XXXXXX)
trap 'rm -rf -- "${temporary}"' EXIT
(
  cd "${temporary}"
  apt-get download "libclang-18-dev=${package_version}"
)
package=$(find "${temporary}" -maxdepth 1 -type f -name 'libclang-18-dev_*.deb' -print -quit)
if [[ -z ${package} ]]; then
  echo 'apt-get did not download the pinned libclang-18-dev package' >&2
  exit 1
fi
observed=$(sha256sum "${package}" | awk '{print $1}')
if [[ ${observed} != ${package_sha256} ]]; then
  echo "package SHA-256 mismatch: ${observed}" >&2
  exit 1
fi

mkdir -p -- "${destination}"
dpkg-deb -x "${package}" "${destination}"
if [[ ! -f "${header_root}/clang/AST/AST.h" ]]; then
  echo 'extracted package does not contain the expected Clang 18 header' >&2
  exit 1
fi
echo "PASS clang_include=${header_root} package_sha256=${observed}"

