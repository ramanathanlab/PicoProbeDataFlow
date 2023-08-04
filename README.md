# PicoProbeDataFlow
Data pipeline infrastructure for ANL PicoProbe project

See `examples/` folder for specific ussage.

## Development

### Installation
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

### Globus Search Index
PicoProbe uses Globus Search to index data. To configure Globus Search, run:
```bash
globus-search index --help
globus-search login
globus-search index list
globus-search index create picoprobe_test picoprobe_testing
globus-search index show 06625170-a9ee-4d68-b8dc-2480c9407966
```

### Configure a Globus Compute Endpoint
```bash
globus-compute-endpoint list
globus-compute-endpoint start AlexsMacBookPro-06-2023
```
**Note**: Replace `AlexsMacBookPro-06-2023` with the name of your endpoint.

## Usage
To start the `tar_and_transfer` flow,
- First start the `globus-compute-endpoint`.
- Then, make sure your globus endpoints are activated.
```bash
source examples/tar_and_transfer/env.sh
python  examples/tar_and_transfer/main.py -l ~/GlobusEndpoint/transfer-flow-test-send
```

To start the `picoprobe_metadata_flow` flow,
```bash
source examples/picoprobe_metadata_flow/env.sh
python  examples/picoprobe_metadata_flow/main.py -l ~/GlobusEndpoint/transfer-flow-test-send
```


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