from gladier import GladierBaseTool, generate_flow_definition


def temporal_image_tool(**data):
    """Given an experiment file (.emd), extract the temporal video and metadata.

    Returns
    -------
    Dict[str, Any]
        The output data dictionary containing the experiment metadata.
    """
    import json
    import shutil
    from pathlib import Path
    import imageio
    import hyperspy.api as hs
    import numpy as np
    import numpy.typing as npt
    import subprocess

    def create_mp4_from_array(a: npt.ArrayLike, output_filename: str, fps: int = 100):
        """Create an MP4 video from a 3D array (T, X, Y)."""
        # Supress type conversion warnings at each iteration
        # logging.getLogger("imageio").setLevel(logging.ERROR)
        bitdepth = 8
        with imageio.get_writer(output_filename, fps=fps) as writer:
            for frame in a:
                # Having this explicit type conversion avoids warnings
                # from imageio and speeds up the code significantly
                mi, ma = np.min(frame), np.max(frame)
                im = (frame - mi) / (ma - mi) * (
                    np.power(2.0, bitdepth) - 1
                ) + 0.499999999
                im = im.astype(np.uint8)
                writer.append_data(im)  # Write each frame

    def run_yolo(source_path: str, model_path: str) -> str:
        """Run a pre-trained YOLOv8 model on a source video file."""
        command = f"yolo task=detect mode=predict model={model_path} conf=0.25 source='{source_path}' save=True"
        output_dir = Path(source_path).parent
        subprocess.run(command, cwd=output_dir, shell=True)

        # Collect the output file with the predictions
        prediction_path = (
            output_dir / "runs" / "detect" / "predict" / Path(source_path).name
        )

        # Move the prediction file to the output directory
        final_prediction_path = output_dir / f"prediction-{prediction_path.name}"
        shutil.move(prediction_path, final_prediction_path)

        # Clean up the yolo output directory
        shutil.rmtree(output_dir / "runs", ignore_errors=True)

        return str(final_prediction_path)

    # General experiment metadata
    metadata = {
        "creators": [{"creatorName": "PicoProbe Team"}],
        "publicationYear": "2023",
        "publisher": "Argonne National Laboratory (ANL)",
        "resourceType": {"resourceType": "Dataset", "resourceTypeGeneral": "Dataset"},
        "subjects": [{"subject": "PicoProbe"}],
        "exp_type": "picoprobe",
    }

    # Unpack the experiment file from the input payload
    experiment_dir = data["publishv2"]["dataset"]
    experiment_file = next(Path(experiment_dir).glob("*.emd"))

    # Load the microscopy dataset and extract metadata
    signals = hs.load(experiment_file)
    experiment_metadata = signals.metadata.as_dictionary()

    # Convert the metadata to JSON (by default it has np.int64, np.float64, etc.)
    experiment_metadata = json.loads(json.dumps(experiment_metadata))

    # Extract a video from the raw signal
    video_file = str(experiment_file.with_suffix(".mp4"))
    create_mp4_from_array(signals._data, video_file, fps=100)

    # Run YOLOv8 on the video to predict nanoparticle locations
    prediction_path = run_yolo(video_file, data["yolo_model_path"])

    # Add the experiment metadata to the general metadata
    metadata["experiment_metadata"] = experiment_metadata
    metadata["temporal_data"] = video_file
    metadata["temporal_prediction_data"] = prediction_path

    # Update the output data with the experiment metadata
    final_data = data["publishv2"]
    final_data["metadata"] = metadata

    # Save the metadata to a file
    metadata_file = experiment_file.with_suffix(".json")
    with open(metadata_file, "w") as f:
        f.write(json.dumps(final_data, indent=4))

    return final_data


@generate_flow_definition(modifiers={temporal_image_tool: {"WaitTime": 28800}})
class TemporalImageTool(GladierBaseTool):
    funcx_functions = [temporal_image_tool]
    required_input = ["publishv2", "yolo_model_path"]
