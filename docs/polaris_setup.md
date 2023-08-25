# Setup Globus Compute on Polars@ALCF

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