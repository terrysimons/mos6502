# Instructions

I highly encourage installation of pyenv and poetry for best results.

You can lint & run tests with:
```
pip install poetry
pip install nox
nox
```

Or you can run commands manually with:

```
pip install pycodestyle
pip install pydocstyle
pip install pytest
```

And then running:

`pycodestyle --max-line-length=100 --ignore=E741,E743 mos6502`, and `pytest tests`.

Use `pip install -e .` to set up the package as a local dev environment.

You can execute a small test program with `python -m mos5402.core`.
