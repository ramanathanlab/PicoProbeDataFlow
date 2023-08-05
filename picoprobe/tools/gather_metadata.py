from gladier import GladierBaseTool, generate_flow_definition


def gather_metadata(**data):
    import json
    from pathlib import Path
    import hyperspy.api as hs

    # General experiment metadata
    metadata = {
        "creators": [{"creatorName": "PicoProbe Team"}],
        "publicationYear": "2023",
        "publisher": "Argonne National Laboratory (ANL)",
        "resourceType": {"resourceType": "Dataset", "resourceTypeGeneral": "Dataset"},
        "subjects": [{"subject": "PicoProbe"}],
        "exp_type": "picoprobe",
    }

    # Experiment metadata
    e_metadata = {}
    experiment_file = data["publishv2"]["dataset"]

    # TODO: Talk to Nestor to confirm we have all the metadata

    try:
        # Load the microscopy dataset and extract metadata
        signals = hs.load(experiment_file)

        # Load each field from the experiment metadata (e.g., "HAADF", "BFS", etc.)
        for dataset in signals:
            e_metadata[
                dataset.metadata.General.title
            ] = dataset.metadata.as_dictionary()
    except Exception as e:
        print(f"Error loading metadata: {e}")

    # Add the experiment metadata to the general metadata
    metadata["experiment_metadata"] = e_metadata

    # Update the output data with the experiment metadata
    final_data = data["publishv2"]
    final_data["metadata"] = metadata

    # Save the metadata to a file
    metadata_file = Path(experiment_file).parent / "metadata.json"
    with open(metadata_file, "w") as f:
        f.write(json.dumps(final_data, indent=4))

    return final_data


@generate_flow_definition
class GatherMetadata(GladierBaseTool):
    funcx_functions = [gather_metadata]
    required_input = ["funcx_endpoint_compute", "publishv2"]
