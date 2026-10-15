#!/bin/bash
# One-time setup of the rebrew-dev WSL distro (run as root). Idempotent.
set -e
export DEBIAN_FRONTEND=noninteractive
id dev >/dev/null 2>&1 || useradd -m -s /bin/bash dev
printf '[boot]\nsystemd = true\n[user]\ndefault = dev\n[interop]\nappendWindowsPath = false\n' > /etc/wsl.conf
apt-get update -qq
apt-get install -y -qq docker.io git curl ca-certificates build-essential python3 python3-venv binutils file >/dev/null
usermod -aG docker dev
su - dev -c 'command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh' >/dev/null
echo "setup ok: $(docker --version) | $(gcc --version | head -1) | $(su - dev -c '~/.local/bin/uv --version')"
