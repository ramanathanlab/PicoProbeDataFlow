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

### Setup a Globus Shared Endpoint on Eagle
This enables Globus transfers (and Compute) read/write access for the PicoProbe data directory on Eagle:
```bash
setfacl -R -d -m group:APSDataAnalysis:rwx /eagle/APSDataAnalysis/PICOPROBE/
```

### Setup a Globus Compute endpoint on Polaris
On a login node run:
```bash
module load conda/2023-01-10-unstable
conda create -n picoprobe python=3.10
conda activate picoprobe
pip install -U pip setuptools wheel
pip install -r requirements/requirements.txt
pip install -e .

globus-compute-endpoint configure picoprobe-non-compute
globus-compute-endpoint start picoprobe-non-compute
```

Now we will need to update the globus-compute-endpoint configuration to use the 
correct python version and add any user groups that require access. To do this, modify:
```console
~/.globus_compute/picoprobe-non-compute/config.py
```

By adding this as an argument to the `LocalProvider`: 
```python
worker_init="module load conda/2023-01-10-unstable; conda activate picoprobe"
```

To get the endpoint ID run,
```bash
globus-compute-endpoint list
```

### Setup a Globus Compute endpoint on a Polaris compute node
```bash
qsub -I -l select=1 -l walltime=1:00:00 -A RL-fold -q debug -l filesystems=home:eagle
module load conda/2023-01-10-unstable
conda activate
conda create -n picoprobe-compute --clone base
conda activate picoprobe-compute
git clone https://github.com/ramanathanlab/PicoProbeDataFlow.git
cd PicoProbeDataFlow
pip install -U pip setuptools wheel
pip install -r requirements/requirements.txt
pip install -e .
```

Attempt 2:
```bash
qsub -I -l select=1 -l walltime=1:00:00 -A RL-fold -q debug -l filesystems=home:eagle
module load conda/2023-01-10-unstable
conda create -n picoprobe-compute-v2 python=3.10 -y
conda activate picoprobe-compute-v2
pip install -U pip setuptools wheel
pip install -r requirements/polaris_gc_requirements.txt

globus-compute-endpoint list
globus-compute-endpoint configure picoprobe-compute
```

Configure the endpoint, by adding these settings to `~/.globus_compute/picoprobe-compute/config.yaml`
```yaml
engine:
    type: HighThroughputEngine
    max_workers_per_node: 1

    # Un-comment to give each worker exclusive access to a single GPU
    available_accelerators: 4

    strategy:
        type: SimpleStrategy
        max_idletime: 300

    address:
        type: address_by_interface
        ifname: bond0

    provider:
        type: PBSProProvider

        launcher:
            type: MpiExecLauncher
            # Ensures 1 manger per node, work on all 64 cores
            bind_cmd: --cpu-bind
            overrides: --depth=64 --ppn 1

        account: RL-fold
        queue: preemptable
        cpus_per_node: 32
        select_options: ngpus=4

        # e.g., "#PBS -l filesystems=home:grand:eagle\n#PBS -k doe"
        scheduler_options: "#PBS -l filesystems=home:grand:eagle"

        # Node setup: activate necessary conda environment and such
        worker_init: "module load conda/2023-01-10-unstable; conda activate picoprobe-compute-v2"

        walltime: 01:00:00
        nodes_per_block: 1
        init_blocks: 0
        min_blocks: 0
        max_blocks: 2
```

Finally, to start the compute endpoint, run:
```bash
globus-compute-endpoint start picoprobe-compute
```

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

### Configuring Windows10
To setup the watcher application on a Windows10 machine:
1. First download python and git
2. Open powershell
3. Navigate to an installation directory of your choice (using `cd`)
4. Download the PicoprobeDataFlow package:
```console
git clone https://github.com/ramanathanlab/PicoProbeDataFlow.git
```
1. Run the following command to enable the creation of a virtual environment: 
```console
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
1. Create a virtual environment (afterwards, you should see (env) at the start of your prompt):
```console
python -m venv env
.\env\Scripts\activate
``` 
1. Install the package and dependencies:
```console
pip install -U setuptools wheel
pip install -r .\requirements\windows_requirements.txt
pip install -e .
```