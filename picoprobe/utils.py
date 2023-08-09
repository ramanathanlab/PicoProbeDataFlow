import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from pprint import pprint
from threading import Event
from typing import Dict, Set, Type, TypeVar, Union

import yaml
from gladier import GladierBaseClient
from pydantic import BaseModel as _BaseModel
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

PathLike = Union[str, Path]
FlowInputType = Dict[str, Dict[str, Union[str, bool, int, float]]]

_T = TypeVar("_T")


class BaseModel(_BaseModel):
    """Base model to provide an easier interface to read/write YAML files."""

    def dump_yaml(self, filename: PathLike) -> None:
        with open(filename, mode="w") as fp:
            yaml.dump(json.loads(self.json()), fp, indent=4, sort_keys=False)

    @classmethod
    def from_yaml(cls: Type[_T], filename: PathLike) -> _T:
        with open(filename) as fp:
            raw_data = yaml.safe_load(fp)
        return cls(**raw_data)  # type: ignore


class GlobusEndpoint(BaseModel):
    """Represent a Globus endpoint."""

    endpoint_id: str
    """The Globus endpoint ID (e.g., "ddb59af0-6d04-11e5-ba58-22000b92c6ec")."""
    rel_path: Path
    """The relative path to the endpoint (e.g., "globus_endpoint/subdir")."""
    abs_path: Path
    """The absolute path to the endpoint (e.g., "/path/to/globus_endpoint/subdir")."""

    def to_relative(self, path: PathLike, subdir: PathLike = "") -> str:
        """Return the file name relative to the globus endpoint root path.

        Parameters
        ----------
        path : str
            The path to the file (e.g., "/path/to/globus_endpoint/file.txt")
        subdir : str, optional
            The subdirectory of the endpoint (e.g., "subdir" of "/path/to/globus_endpoint/subdir/file.txt")

        Returns
        -------
        str
            The path relative to the endpoint root (e.g., "globus_endpoint/file.txt")
        """
        return str(self.rel_path / subdir / Path(path).name)

    def to_absolute(self, path: PathLike, subdir: PathLike = "") -> str:
        """Return the absolute file name.

        Parameters
        ----------
        path : str
            The path to the file in the globus endpoint (e.g., "globus_endpoint/file.txt")
        subdir : str, optional
            The subdirectory of the endpoint (e.g., "subdir" of "globus_endpoint/subdir/file.txt")

        Returns
        -------
        str
            The absolute path (e.g., "/path/to/globus_endpoint/file.txt")
        """
        return str(self.abs_path / subdir / Path(path).name)


class Watcher:
    def __init__(
        self,
        directory: PathLike,
        handler: FileSystemEventHandler = FileSystemEventHandler(),
    ) -> None:
        self.observer = Observer()
        self.handler = handler
        self.directory = directory

        # Provide a method to stop the watcher (w.done.set())
        self.done = Event()

    def run(self) -> None:
        self.observer.schedule(self.handler, self.directory, recursive=True)  # type: ignore
        self.observer.start()  # type: ignore
        print(f"\nWatcher Running in {self.directory}/\n")
        try:
            while not self.done.is_set():
                time.sleep(1)
        except Exception as e:
            print(f"Watcher caught exception: {e}")
        finally:
            self.observer.stop()  # type: ignore

        self.observer.join()
        print("\nWatcher Terminated\n")


class CheckPoint:
    def __init__(self, checkpoint_file: PathLike) -> None:
        self.checkpoint_file = Path(checkpoint_file)

        # Initialize a seen events set to not repeat past flows
        self.seen_events: Set[str] = set()
        if self.checkpoint_file.exists():
            self.load_checkpoint()

    def load_checkpoint(self) -> None:
        self.seen_events = set(self.checkpoint_file.read_text().split("\n"))

    def save_checkpoint(self, event: str) -> None:
        self.seen_events.add(event)
        with open(self.checkpoint_file, "a+") as f:
            f.write(f"{event}\n")

    def seen(self, event: str) -> bool:
        """Returns True if the `event` has been seen, otherwise returns False."""
        if event in self.seen_events:
            return True
        self.save_checkpoint(event)
        return False


class BaseFlowHandler(FileSystemEventHandler, ABC):
    def __init__(self, flow_client: GladierBaseClient, checkpoint: CheckPoint) -> None:
        super().__init__()
        self.flow_client = flow_client
        self.checkpoint = checkpoint

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
        # Run the flow
        flow = self.flow_client.run_flow(flow_input=flow_input, label=run_label)

        # Log the flow information
        # DEV Note: get_flow_id() must be called after run_flow(), otherwise it will be None
        flow_id = self.flow_client.get_flow_id()
        print("Flow created with ID: " + flow_id)
        print("https://app.globus.org/flows/" + flow_id)
        print("")
        pprint(self.flow_client.get_flow_definition())
        print("Flow Input:")
        pprint(flow_input)

        # Log the flow run information
        run_id = flow["action_id"]
        print("Flow started with run ID: " + run_id)
        print("https://app.globus.org/runs/" + run_id)
        print("=" * 100)

    @abstractmethod
    def on_any_event(self, event: FileSystemEvent) -> None:
        """Child class should implement."""
