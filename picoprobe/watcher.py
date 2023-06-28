import os
import time
from abc import ABC, abstractmethod
from pprint import pprint
from threading import Event
from typing import Dict, List, Union

from gladier import GladierBaseClient
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

FlowInputType = Dict[str, Dict[str, Union[str, bool, int, float]]]


class MissingEnvironmentVariable(Exception):
    pass


class Watcher:
    def __init__(
        self,
        directory: str = ".",
        handler: FileSystemEventHandler = FileSystemEventHandler(),
    ) -> None:
        self.observer = Observer()
        self.handler = handler
        self.directory = directory

        # Provide a method to stop the watcher (w.done.set())
        self.done = Event()

    def run(self) -> None:
        self.observer.schedule(self.handler, self.directory, recursive=True)
        self.observer.start()
        print(f"\nWatcher Running in {self.directory}/\n")
        try:
            while not self.done.is_set():
                time.sleep(1)
        except Exception as e:
            print(f"Watcher caught exception: {e}")
        finally:
            self.observer.stop()

        self.observer.join()
        print("\nWatcher Terminated\n")


class BaseFlowHandler(FileSystemEventHandler, ABC):
    required_env_vars: List[str] = []

    def __init__(self, flow_client: GladierBaseClient) -> None:
        super().__init__()
        self.flow_client = flow_client
        self.validate_environment()

    def validate_environment(self) -> None:
        """Validate a set of environment variables exist."""
        for var in self.required_env_vars:
            if var not in os.environ:
                raise MissingEnvironmentVariable(var)

    def start_flow(self, flow_input: FlowInputType, run_label: str = "Run") -> None:
        """Start a new Globus flow.

        Parameters
        ----------
        flow_input : FlowInputType
            The input arguments to the flow.
        run_label : str, optional
            Label for the current run (This is the label that will be
            presented on the globus webApp), by default "Run"
        """
        # Log the flow information
        flow_id = self.flow_client.get_flow_id()
        print("Flow created with ID: " + flow_id)
        print("https://app.globus.org/flows/" + flow_id)
        print("")
        pprint(self.flow_client.get_flow_definition())
        print("Flow Input:")
        pprint(flow_input)

        # Run the flow
        flow = self.flow_client.run_flow(flow_input=flow_input, label=run_label)

        # Log the flow run information
        run_id = flow["action_id"]
        print("Flow started with run ID: " + run_id)
        print("https://app.globus.org/runs/" + run_id)
        print("=" * 100)

    @abstractmethod
    def on_any_event(self, event: FileSystemEvent) -> None:
        """Child class should implement."""
