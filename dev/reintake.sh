export REBREW_TOOLCHAINS_DIR=~/recompile-toolchains PATH=$HOME/.local/bin:$PATH
rm -rf ~/proj-toy && mkdir ~/proj-toy && cd ~/proj-toy
rebrew intake ~/targets/toy --toolchain gcc-14.2.0 --json 2>&1 | tail -5
echo ---; grep -E 'profile|arch|format' rebrew-project.toml | head
