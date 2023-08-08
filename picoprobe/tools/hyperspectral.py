from gladier import GladierBaseTool, generate_flow_definition


def hyperspectral_image_tool(**data):
    """Given an experiment file (.emd), extract the hyperspectral image and metadata.

    Returns
    -------
    Dict[str, Any]
        The output data dictionary containing the experiment metadata.

    Raises
    ------
    ValueError
        If no hyperspectral image is found in the experiment file.
    """
    import json
    import hyperspy.api as hs
    import matplotlib.pyplot as plt
    import numpy as np
    import numpy.typing as npt
    from typing import Optional, Tuple, Dict, Any

    def load_hyperspectral_image(
        experiment_file: str,
    ) -> Tuple[npt.ArrayLike, npt.ArrayLike, Dict[str, Any]]:
        """Load the hyperspectral image from the experiment file.

        Parameters
        ----------
        experiment_file : str
            The path to the experiment file.

        Returns
        -------
        npt.ArrayLike
            The hyperspectral image with shape (X, Y, S).
        np.ArrayLike
            Energy axis with shape (S,).
        Dict[str, Any]
            The metadata dictionary (JSON data).

        Raises
        ------
        ValueError
            If no hyperspectral image is found in the experiment file.
        """
        # Load the hyperspectral image
        signals = hs.load(experiment_file)

        # Find the hyperspectral image by checking the data dimensionality
        for signal in signals:
            if signal._data.ndim == 3:
                # Extract the hyperspectral image
                hs_image = signal._data
                # Extract the metadata for the hyperspectral image
                metadata = signal.metadata.as_dictionary()
                break
        else:
            raise ValueError(
                f"No hyperspectral image found in experiment file: {experiment_file}"
            )

        # These should be read from the metadata it will change with instrument
        x_offset = -479.0021  # The zero channel enegry offset in eV
        x_increment = 5  # The evch
        n_channels = hs_image.shape[2]  # The number of channels

        # Compute the energy axis
        energy = (x_offset + x_increment * np.arange(n_channels)) / 1000.0

        return hs_image, energy, metadata

    def plot_hyperspectral_image(
        hs_image: npt.ArrayLike, energy: npt.ArrayLike, savefile: Optional[str] = None
    ) -> None:
        """Plot the hyperspectral image and spectrum.

        Parameters
        ----------
        hs_image : npt.ArrayLike
            The hyperspectral image with shape (X, Y, S).
        energy : npt.ArrayLike
            The energy axis with shape (S,).
        savefile : Optional[str], optional
            A path to save the plot .png file, by default None
        """
        fig, (ax_im, ax_spec) = plt.subplots(1, 2, figsize=(15, 5))

        # Configure Image subplot
        ax_im.set(xlabel="x [pixel]", ylabel="y [pixel]")
        im = ax_im.imshow(hs_image.sum(axis=2), cmap="Blues_r", interpolation="nearest")
        colorbar = fig.colorbar(im, ax=ax_im)
        colorbar.set_label("Intensity")

        # Configure Spectrum subplot
        ax_spec.set(
            ylabel="XEDS counts", xlabel="Energy (keV)", yscale="log", title="Spectrum"
        )
        ax_spec.plot(energy, hs_image.sum(axis=(0, 1)), lw=2)

        if savefile:
            plt.savefig(savefile, dpi=300, bbox_inches="tight")

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
    experiment_file = data["publishv2"]["dataset"]

    # Load the microscopy dataset and extract metadata
    hs_image, energy, experiment_metadata = load_hyperspectral_image(experiment_file)

    # Plot the hyperspectral image and spectrum
    plot_file = experiment_file.replace(".emd", "-hyperspectral.png")
    plot_hyperspectral_image(hs_image, energy, plot_file)

    # Add the experiment metadata to the general metadata
    metadata["experiment_metadata"] = experiment_metadata
    metadata["hyperspectral_image"] = plot_file

    # Update the output data with the experiment metadata
    final_data = data["publishv2"]
    final_data["metadata"] = metadata

    # Save the metadata to a file
    metadata_file = experiment_file.replace(".emd", "-metadata.json")
    with open(metadata_file, "w") as f:
        f.write(json.dumps(final_data, indent=4))

    return final_data


@generate_flow_definition
class HyperspectralImageTool(GladierBaseTool):
    funcx_functions = [hyperspectral_image_tool]
    required_input = ["funcx_endpoint_compute", "publishv2"]
