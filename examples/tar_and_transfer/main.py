import os
from argparse import ArgumentParser
from pathlib import Path

from gladier import GladierBaseClient, generate_flow_definition
from watchdog.events import FileSystemEvent

from picoprobe.watcher import BaseFlowHandler, FlowInputType, Watcher


@generate_flow_definition
class TarAndTransfer(GladierBaseClient):
    gladier_tools = [
        "gladier_tools.posix.Tar",
        "gladier_tools.globus.Transfer",
    ]


class TarAndTransferFlowHandler(BaseFlowHandler):
    required_env_vars = [
        "LOCAL_FUNCX_ENDPOINT",
        "LOCAL_GLOBUS_ENDPOINT",
        "REMOTE_FUNCX_ENDPOINT",
        "REMOTE_GLOBUS_ENDPOINT",
    ]

    def __init__(self, remote_directory: str, flow_client: GladierBaseClient) -> None:
        super().__init__(flow_client)
        self.remote_directory = remote_directory

    def create_flow_input(self, src_path: str) -> FlowInputType:
        flow_input = {
            "input": {
                # ============================
                # The inputs to the Tar action
                # The directory below should exist with files. It will be archived by the Tar Tool.
                "tar_input": src_path,
                # Set this to your own funcx endpoint where you want to tar files
                "funcx_endpoint_compute": os.getenv("LOCAL_FUNCX_ENDPOINT"),
                # ============================
                # The inputs to the Transfer
                # Set this to the globus endpoint where your tarred archive has been created
                "transfer_source_endpoint_id": os.getenv("LOCAL_GLOBUS_ENDPOINT"),
                # By default, this will transfer the tar file to Globus Tutorial Endpoint 1
                "transfer_destination_endpoint_id": os.getenv("REMOTE_GLOBUS_ENDPOINT"),
                # By default, the Tar Tool will append '.tgz' to the archive it creates
                "transfer_source_path": f"{src_path}.tgz",
                "transfer_destination_path": f"{self.remote_directory}/{Path(src_path).name}.tgz",
                "transfer_recursive": False,
                # ============================
            }
        }
        return flow_input

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory and event.event_type == "created":
            directory = Path(event.src_path)
            # If the directory is empty, return
            if not any(directory.iterdir()):
                return

            # TODO: On restart, it might be good to keep a "seen" list
            #       to avoid restarting old flows.

            #  Otherwise, start a new flow using the directory inputs
            flow_input = self.create_flow_input(event.src_path)
            self.start_flow(flow_input, run_label=f"TarAndTransfer {directory.name}")


if __name__ == "__main__":
    # Parse user arguments
    parser = ArgumentParser()
    parser.add_argument("-l", "--local_directory", required=True)
    parser.add_argument("-r", "--remote_directory", required=True)
    args = parser.parse_args()

    # Instantiate the flow client
    flow_client = TarAndTransfer()

    # Instantiate watcher which launches flows based on a flow handler
    flow_handler = TarAndTransferFlowHandler(args.remote_directory, flow_client)
    w = Watcher(args.local_directory, flow_handler)

    # Start the flow
    w.run()
