SP=$(/home/dev/fork-venv/bin/python -c 'import rebrew,os;print(os.path.dirname(rebrew.__file__))')
echo "rebrew at: $SP"
/home/dev/fork-venv/bin/python /mnt/c/debug/rebrew-wtf/dev/patch_rebrew_elf.py "$SP"
