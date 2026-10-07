#!/usr/bin/env bash
# Clone the working environment, or rebuild its official Arch package set.
set -euo pipefail
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mode=clone
source_box=codex-tools
name=codex-tools-copy
with_desktop=0
while (($#)); do
  case "$1" in
    --fresh) mode=fresh; shift ;;
    --source) source_box=${2:?Missing source name}; shift 2 ;;
    --name) name=${2:?Missing destination name}; shift 2 ;;
    --with-github-desktop) with_desktop=1; shift ;;
    --help|-h)
      printf '%s\n' 'Usage: recreate-distrobox.sh [--name NAME] [--source NAME] [--fresh] [--with-github-desktop]' 'Default: clone codex-tools to codex-tools-copy, retaining installed packages.' 'Fresh: rebuild official Arch packages; optionally build the GitHub Desktop AUR package.'
      exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done
[[ $name =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ && $source_box =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]] || { echo 'Invalid container name' >&2; exit 2; }
command -v distrobox >/dev/null
command -v podman >/dev/null
if podman container exists "$name"; then
  printf 'Destination already exists: %s. Choose a new name; nothing was replaced.\n' "$name" >&2
  exit 1
fi
if [[ $mode == clone ]]; then
  podman container exists "$source_box" || { printf 'Source not found: %s\n' "$source_box" >&2; exit 1; }
  distrobox create --yes --clone "$source_box" --name "$name"
else
  mapfile -t packages < "$script_dir/../environment/packages.arch.txt"
  distrobox create --yes --image docker.io/library/archlinux:latest --name "$name" --additional-packages "${packages[*]}"
fi
# First entry initializes Distrobox integration for the current host user.
distrobox enter --name "$name" -- true
if [[ $mode == fresh && $with_desktop == 1 ]]; then
  podman exec --user root "$name" pacman -Syu --needed --noconfirm base-devel curl git libsecret libxss nspr nss unzip
  # AUR recipes execute build scripts. This flag explicitly opts into that build.
  distrobox enter --name "$name" -- bash -lc '
    set -euo pipefail
    work=$(mktemp -d /tmp/dropmux-desktop-build.XXXXXX)
    git clone https://aur.archlinux.org/github-desktop-bin.git "$work/source"
    cd "$work/source"
    makepkg --nodeps --noconfirm
    printf "Built packages are in %s\n" "$work/source"
  '
  # Install only package files generated in the dedicated build directories.
  podman exec --user root "$name" bash -lc 'mapfile -d "" files < <(find /tmp/dropmux-desktop-build.*/source -maxdepth 1 -name "*.pkg.tar.zst" -print0); ((${#files[@]})) || exit 1; pacman -U --noconfirm "${files[@]}"'
fi
printf 'Ready: distrobox enter --name %s\n' "$name"
printf 'Dropmux: distrobox enter --name %s -- python3 /path/to/Dropmux/dropmux.py --show\n' "$name"
