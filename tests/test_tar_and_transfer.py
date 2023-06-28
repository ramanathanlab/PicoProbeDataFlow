import os
import sys
import tempfile
import threading
import time
from pathlib import Path

from examples.tar_and_transfer.main import TarAndTransfer, TarAndTransferFlowHandler
from picoprobe.watcher import FlowInputType, Watcher

sys.path.append("../examples")


class MockTarAndTransferFlowHandler(TarAndTransferFlowHandler):
    def start_flow(self, flow_input: FlowInputType, run_label: str) -> None:
        print(f"Starting flow with input:\n{flow_input}\n")


def test_mock_flow():
    # Need to set environment variables to pass validation
    os.environ["LOCAL_FUNCX_ENDPOINT"] = ""
    os.environ["LOCAL_GLOBUS_ENDPOINT"] = ""
    os.environ["REMOTE_FUNCX_ENDPOINT"] = ""
    os.environ["REMOTE_GLOBUS_ENDPOINT"] = ""

    # Instantiate the flow client
    flow_client = TarAndTransfer()

    # Instantiate the flow client
    flow_client = TarAndTransfer()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Instantiate watcher which launches flows based on a flow handler
        flow_handler = MockTarAndTransferFlowHandler(tmpdir, flow_client)
        w = Watcher(tmpdir, flow_handler)

        # Start the mock flow
        t = threading.Thread(target=w.run)
        t.start()

        # Give the watcher time to start before creating a directory
        time.sleep(1)

        # Create a new directory in the watched directory
        new_dir = Path(tmpdir) / "new_dir"
        new_dir.mkdir()
        (new_dir / "data.txt").touch()

        # Give the watcher time to notice the directory and invoke `start_flow`
        time.sleep(1)

        # Signal the watcher to stop
        w.done.set()
