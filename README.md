# PicoProbeDataFlow
Data flow infrastructure for Argonne National Laboratory PicoProbe project.

## Dataset
- The datasets used in this study can be downloaded here: https://zenodo.org/record/8284219
- The machine learning nanoparticle prediciton dataset: https://app.roboflow.com/picoprobe/nanoparticle-detection/1

## Installation
On macOS, Linux:
```
python3 -m venv env
source env/bin/activate
pip3 install -U pip setuptools wheel
pip3 install -r requirements/dev.txt
pip3 install -r requirements/requirements.txt
pip3 install -e .
```

On Windows, see `docs/windows_setup.md`.

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

### Globus Search Index
PicoProbe uses Globus Search to index data. To configure Globus Search, run:
```bash
globus-search index --help
globus-search login
globus-search index list
globus-search index create picoprobe_test picoprobe_testing
globus-search index show [search-index-uuid]
```
Now give Globus group members permission to write to the search index:
```bash
globus-search index role create --type group <search-index-uuid> writer <group-uuid>
```

### Configure a Globus Compute Endpoint Locally
```bash
globus-compute-endpoint list
globus-compute-endpoint start AlexsMacBookPro-06-2023
```
**Note**: Replace `AlexsMacBookPro-06-2023` with the name of your endpoint.

## Usage
Please follow the instructions in `docs/windows_setup.md`. 

**Note**: The Windows-specific commands can be ignored if you are running on a different system.

We also provide instructions to generate flow runtime statistics in `docs/windows_setup.md`.

## Training the Machine Learning Model
The easiest way to reproduce the nanoparticle detection model is to make an accont on [Roboflow](https://roboflow.com/) and then run our notebook in Google Colab: [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ramanathanlab/PicoProbeDataFlow/blob/main/examples/xloop2023/machine_learning/train_yolov8_object_detection_on_custom_dataset.ipynb)

**Note**: Make sure to add your Roboflow API key on the code cell with the `YOUR_API_KEY` placeholder.

If you are interested in buidling the dataset manually, please see `examples/xloop2023/machine_learning/build_yolov8_dataset.ipynb` for how to convert the EMD data files to PNG images for YOLOv8 compatibilty.

## Django Globus Portal Framework (DGPF) Data Portal
We provide an interactive visualization of our experimental results using the source code at [this](https://github.com/ramanathanlab/picoprobe-portal/tree/main) repository.

