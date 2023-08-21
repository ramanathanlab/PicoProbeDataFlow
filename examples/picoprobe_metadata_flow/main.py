from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from pprint import pprint

from gladier import GladierBaseClient, generate_flow_definition
from watchdog.events import FileSystemEvent

from picoprobe.tools.hyperspectral import HyperspectralImageTool
from picoprobe.utils import (
    BaseFlowHandler,
    BaseModel,
    CheckPoint,
    FlowInputType,
    GlobusEndpoint,
    Watcher,
)


@generate_flow_definition(
    modifiers={
        "hyperspectral_image_tool": {"endpoint": "funcx_endpoint_non_compute"},
        "publishv2_gather_metadata": {
            "payload": "$.HyperspectralImageTool.details.results[0].output"
        },
    }
)
class PicoProbeMetadataFlow_Production_v5(GladierBaseClient):
    gladier_tools = [
        "gladier_tools.globus.Transfer",
        HyperspectralImageTool,
        "gladier_tools.publish.Publishv2",
    ]


class PicoProbeFlowConfig(BaseModel):
    local_globus_endpoint: GlobusEndpoint
    remote_globus_endpoint: GlobusEndpoint
    remote_funcx_endpoint: str
    remote_funcx_endpoint_non_compute: str
    globus_search_index: str


class PicoProbeMetadataFlowHandler(BaseFlowHandler):
    def __init__(
        self,
        config: PicoProbeFlowConfig,
        flow_client: GladierBaseClient,
        checkpoint: CheckPoint,
    ) -> None:
        super().__init__(flow_client, checkpoint)

        self.config = config
        self.local = config.local_globus_endpoint
        self.remote = config.remote_globus_endpoint

    def create_flow_input(self, src_path: str) -> FlowInputType:
        # Put remote data inside a time-stamped directory
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        # Path to the remote directory containing experiment results and analysis
        remote_experiment_dir = self.remote.to_absolute(src_path, ts)
        remote_experiment_dir = Path(remote_experiment_dir).parent.as_posix()

        flow_input = {
            "input": {
                # Step 1. Transfer from local to remote
                # ============================
                "transfer_source_endpoint_id": self.local.endpoint_id,
                "transfer_destination_endpoint_id": self.remote.endpoint_id,
                "transfer_source_path": self.local.to_relative(src_path),
                "transfer_destination_path": self.remote.to_relative(src_path, ts),
                "transfer_recursive": False,
                # ============================
                # Step 2-3. Gather metadata from the remote file, plot the hyperspectral image
                # and publish the metadata to Globus Search
                "funcx_endpoint_compute": self.config.remote_funcx_endpoint,
                "funcx_endpoint_non_compute": self.config.remote_funcx_endpoint,
                "publishv2": {
                    "dataset": remote_experiment_dir,
                    "destination": remote_experiment_dir,
                    "source_collection": self.remote.endpoint_id,
                    "destination_collection": self.remote.endpoint_id,
                    "index": self.config.globus_search_index,
                    "metadata": {},  # Populated in the HyperspectralImageTool
                    "ingest_enabled": True,
                    "transfer_enabled": False,
                    "visible_to": ["public"],
                },
                # ============================
            }
        }
        print(flow_input)
        return flow_input

    def on_any_event(self, event: FileSystemEvent) -> None:
        if not event.is_directory and event.event_type == "created":
            file = Path(event.src_path)

            # Skip non-emd files
            if not file.suffix == ".emd":
                return

            # Check to see if the file has been seen before and, if so, skip it
            if self.checkpoint.seen(event.src_path):
                return

            #  Otherwise, start a new flow using the directory inputs
            flow_input = self.create_flow_input(event.src_path)

            # Start the flow with the new file as input
            self.start_flow(flow_input, run_label=f"Hyperspectral {file.name}")


if __name__ == "__main__":
    # Parse user arguments
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", type=Path, required=True)
    parser.add_argument("-l", "--local_dir", type=Path, required=True)
    parser.add_argument(
        "-p", "--checkpoint_file", type=Path, default="gladier-checkpoint.txt"
    )
    args = parser.parse_args()

    # Load the configuration file
    config = PicoProbeFlowConfig.from_yaml(args.config)

    # Log the configuration
    print("Configuration:")
    pprint(config)

    # Instantiate the flow client
    flow_client = PicoProbeMetadataFlow_Production_v5()

    # Instantiate watcher which launches flows based on a flow handler
    checkpoint = CheckPoint(args.checkpoint_file)
    flow_handler = PicoProbeMetadataFlowHandler(config, flow_client, checkpoint)
    w = Watcher(args.local_dir, flow_handler)

    # Start the flow
    w.run()
