# PicoProbeDataFlow
Data flow infrastructure for Argonne National Laboratory PicoProbe.


![overview](https://github.com/ramanathanlab/PicoProbeDataFlow/assets/38300604/046dc3cd-03aa-4652-976d-7ea7d8b3c6e2)

## Dataset
- The datasets used in this study can be downloaded here: https://zenodo.org/record/8284219
- The machine learning nanoparticle prediciton dataset: https://app.roboflow.com/picoprobe/nanoparticle-detection/1

For convenience, here is a command to download the zenodo dataset. It is a 1.32 GB tarball:
```bash
wget https://zenodo.org/record/8284219/files/data.tar.gz
```

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

### Globus Transfer setup
For running locally, install [Globus Personal Connect](https://www.globus.org/globus-connect-personal). 

### Globus Compute setup
Configure a Globus Compute Endpoint locally:
```bash
globus-compute-endpoint list
globus-compute-endpoint start AlexsMacBookPro-06-2023
```
**Note**: Replace `AlexsMacBookPro-06-2023` with the name of your endpoint.

**Note**: To setup Globus Compute on Polaris@ALCF, see `docs/polaris_setup.md`.

### Globus Search Index setup
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

## Usage
You will need to collect the UUIDs for the Globus tools (Transfer, Compute, Search) and add them to
a configuration YAML file. The Transfer tool also requires the the absolute path (and Globus-relative) 
of the Globus endpoint you are using. For an example configuration, please see:
- For the Hyperspectral flow: `examples/hyperspectral_flow/config/macbook_test.yaml`
- For the Spatiotemporal flow: `examples/spatiotemporal_flow/config/macbook_to_polaris_compute.yaml`

For detailed usage, please follow the instructions in `docs/windows_setup.md`. 

**Note**: The Windows-specific commands can be ignored if you are running on a different system.

We also provide instructions to generate flow runtime statistics in `docs/windows_setup.md`.

## Training the Machine Learning Model
The easiest way to reproduce the nanoparticle detection model is to make an accont on [Roboflow](https://roboflow.com/) and then run our notebook in Google Colab: [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ramanathanlab/PicoProbeDataFlow/blob/main/examples/xloop2023/machine_learning/train_yolov8_object_detection_on_custom_dataset.ipynb)

**Note**: Make sure to add your Roboflow API key on the code cell with the `YOUR_API_KEY` placeholder.

If you are interested in buidling the dataset manually, please see `examples/xloop2023/machine_learning/build_yolov8_dataset.ipynb` for how to convert the EMD data files to PNG images for YOLOv8 compatibilty.

## Django Globus Portal Framework (DGPF) Data Portal
We provide an interactive visualization of our experimental results using the source code at [this](https://github.com/ramanathanlab/picoprobe-portal/tree/main) repository.
