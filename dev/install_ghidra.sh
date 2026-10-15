set -e
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openjdk-21-jdk-headless >/dev/null 2>&1 || apt-get install -y -qq default-jdk-headless >/dev/null 2>&1
java -version 2>&1 | head -1
su - dev -c 'export REBREW_TOOLCHAINS_DIR=~/recompile-toolchains PATH=$HOME/.local/bin:$PATH; /home/dev/fork-venv/bin/python -c "from decompnet import toolchains; print(toolchains.install(\"ghidra\"))"' 2>&1 | tail -3
echo GHIDRA_DONE
