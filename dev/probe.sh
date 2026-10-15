cd ~
R=$(~/.local/share/uv/tools/rebrew/bin/python -c 'import rebrew,os;print(os.path.dirname(rebrew.__file__))')
echo "$R"; ls "$R" | tr '\n' ' '; echo
grep -rn "^def \|^async def " "$R"/compile*.py "$R"/test*.py "$R"/matcher/*.py 2>/dev/null | grep -iE "compile|obj|extract|compare|test" | head -30
