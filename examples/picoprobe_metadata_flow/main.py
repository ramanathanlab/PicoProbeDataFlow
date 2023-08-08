import os
from argparse import ArgumentParser
from pathlib import Path
from gladier import GladierBaseClient, generate_flow_definition
from watchdog.events import FileSystemEvent

from picoprobe.tools.hyperspectral import HyperspectralImageTool
from picoprobe.utils import (
    BaseFlowHandler,
    CheckPoint,
    FlowInputType,
    GlobusEndpoint,
    Watcher,
)


# @generate_flow_definition(
#     modifiers={
#         "publishv2_gather_metadata": {"payload": "$.GatherMetadata.details.result[0]"}
#     }
# )


@generate_flow_definition
class PicoProbeMetadataFlow_v3(GladierBaseClient):
    gladier_tools = [
        "gladier_tools.globus.Transfer",
        HyperspectralImageTool,
        # "gladier_tools.publish.Publishv2",
    ]


class PicoProbeMetadataFlowHandler(BaseFlowHandler):
    required_env_vars = [
        # Local Transfer
        "LOCAL_GLOBUS_ENDPOINT",
        "LOCAL_GLOBUS_REL_PATH",
        "LOCAL_GLOBUS_ABS_PATH",
        # Remote Transfer
        "REMOTE_GLOBUS_ENDPOINT",
        "REMOTE_GLOBUS_REL_PATH",
        "REMOTE_GLOBUS_ABS_PATH",
        # Remote Compute
        "REMOTE_FUNCX_ENDPOINT",
    ]

    def __init__(self, flow_client: GladierBaseClient, checkpoint: CheckPoint) -> None:
        super().__init__(flow_client, checkpoint)

        self.local = GlobusEndpoint(
            os.environ["LOCAL_GLOBUS_ENDPOINT"],
            os.environ["LOCAL_GLOBUS_REL_PATH"],
            os.environ["LOCAL_GLOBUS_ABS_PATH"],
        )
        self.remote = GlobusEndpoint(
            os.environ["REMOTE_GLOBUS_ENDPOINT"],
            os.environ["REMOTE_GLOBUS_REL_PATH"],
            os.environ["REMOTE_GLOBUS_ABS_PATH"],
        )

    def create_flow_input(self, src_path: str) -> FlowInputType:
        flow_input = {
            "input": {
                # Step 1. Transfer from local to remote
                # ============================
                "transfer_source_endpoint_id": self.local.endpoint_id,
                "transfer_destination_endpoint_id": self.remote.endpoint_id,
                "transfer_source_path": self.local.to_relative(src_path),
                "transfer_destination_path": self.remote.to_relative(src_path),
                "transfer_recursive": False,
                # ============================
                # Step 2. Gather metadata from the remote file
                # TODO: Figure out what the working directory of the funcx endpoint is
                "funcx_endpoint_compute": os.getenv("REMOTE_FUNCX_ENDPOINT"),
                # "funcx_endpoint_non_compute": os.getenv("REMOTE_FUNCX_ENDPOINT"),
                "publishv2": {
                    "dataset": self.remote.to_absolute(src_path),
                    # "index": "aefcecc6-e554-4f8c-a25b-147f23091944",
                    # "project": "reports",
                    # "source_collection": "eeabbb24-b47d-11ed-a504-1f2a3a60e896",
                    # "source_collection_basepath": "/",
                    # "destination_collection": "bb8d048a-2cad-4029-a9c7-671ec5d1f84d",
                    "metadata": {},
                    # "ingest_enabled": True,
                    # "transfer_enabled": True,
                    # "destination": str("/portal/reports/" + str(dest_path)),
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
            self.start_flow(flow_input, run_label=f"TarAndTransfer {file.name}")


if __name__ == "__main__":
    # Parse user arguments
    parser = ArgumentParser()
    parser.add_argument("-l", "--local_dir", type=Path, required=True)
    parser.add_argument(
        "-c", "--checkpoint_file", type=Path, default="gladier-checkpoint.txt"
    )
    args = parser.parse_args()

    # Instantiate the flow client
    flow_client = PicoProbeMetadataFlow_v3()

    # Instantiate watcher which launches flows based on a flow handler
    checkpoint = CheckPoint(args.checkpoint_file)
    flow_handler = PicoProbeMetadataFlowHandler(flow_client, checkpoint)
    w = Watcher(args.local_dir, flow_handler)

    # Start the flow
    w.run()
