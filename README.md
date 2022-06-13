# PicoProbeDataFlow
Data pipeline infrastructure for ANL PicoProbe project

See `examples/` folder for specific ussage.

## Development

Pip Locally:
```
python3 -m venv env
source env/bin/activate
pip3 install -U pip setuptools wheel
pip3 install -r requirements/dev.txt
pip3 install -r requirements/requirements.txt
pip3 install -e .
```

Conda Locally: 
```
conda create -p ./conda-env python=3.9
conda activate ./conda-env
pip install -U pip setuptools wheel
pip install -r requirements/dev.txt
pip install -r requirements/requirements.txt
pip install -e .
```

To run dev tools (flake8, black, mypy): `make`

## Contributing

Please post an issue to request access to push new code, then run:
```
git checkout -b <branchname>
git add <files you want>
git commit -m 'message'
git push
```
Then open a pull request for a code review.

If contributing to the core picoprobe package, please add test cases
mirroring the python module directory/file structure. Test file names
should have the form `test_<module>.py`. Test cases can be run with:
```
pytest test -vs
```

To make the documentation with readthedocs:

```
cd docs/
make html
```