"""Data transfer utilities."""
import logging
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from multiprocessing import Event, Process
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Union
from uuid import uuid4

from balsam.api import ApplicationDefinition, Job
from balsam.config import SiteConfig
from balsam.schemas import JobState
from pydantic import BaseModel, validator

PathLike = Union[str, Path]

logger = logging.getLogger(__name__)

# TODO: Give a reasonable default for expiration_time
def run_untar_loop(
    input_directory: Path,
    untar_interval: float,
    expiration_time: float,
    max_concurrent_untars: int = 10,
) -> None:
    """Periodically untar incoming archives and clean up old .tar archives.

    Parameters
    ----------
    input_directory : Path
        _description_
    untar_interval : float
        Number of seconds between untarring of archives.
    expiration_time : float
        Number of seconds after which a transferred archive can be removed.
    max_concurrent_untars : int, optional
        Number of concurrent untarring workers, by default 10

    Note
    ----
    MUST NOT delete .tar immediately; because Globus will think it failed and
    retry transfer tasks forever (race condition).
    """
    tar_file_ages: Dict[Path, float] = {}
    processes: "List[subprocess.Popen[bytes]]" = []

    while True:
        time.sleep(untar_interval)
        for key in tar_file_ages:
            tar_file_ages[key] += untar_interval

        all_tar_files = set(input_directory.glob("*.tar"))
        seen_tar_files = set(tar_file_ages.keys())
        new_tar_files = all_tar_files - seen_tar_files

        processes = [p for p in processes if p.poll() is None]

        for tar_file in new_tar_files:
            if len(processes) >= max_concurrent_untars:
                logger.debug(f"At {max_concurrent_untars} max concurrent untars")
                break
            logger.info(f"Untarring {tar_file}")
            p = subprocess.Popen(  # pylint: disable=R1732
                f"tar -xvf {tar_file.name}", cwd=input_directory, shell=True
            )
            processes.append(p)
            tar_file_ages[tar_file] = 0.0

        # Only remove tar files that have been around for the expiration_time
        to_remove = [f for f, age in tar_file_ages.items() if age >= expiration_time]
        for f in to_remove:
            f.unlink()
            tar_file_ages.pop(f)


class TransferConfig(BaseModel):
    """Configuration for a data transfer daemon."""

    poll_time: float = 10.0
    """Number of seconds between polling for new files to transfer."""
    patterns: List[str]
    """List of glob patterns to match files to transfer."""
    destination: PathLike
    """Where to transfer files to. Must be either Balsam LOC:PATH string or a local Path."""

    @validator("destination")
    def destination_local_or_remote(cls, v: PathLike) -> PathLike:
        """Validate whether `destination` is local or remote.

        Parameters
        ----------
        v : PathLike
            The transfer destination.

        Returns
        -------
        PathLike
            Returns a str if the destination is remote, otherwise a path.
        """
        return str(v) if ":" in str(v) else Path(v)


class TransferOut(ApplicationDefinition):
    """Application to transfer a single tar file to a remote location using Globus."""

    site = 0
    command_template = "echo no-op"
    cleanup_files = ["payload-*.tar"]
    transfers = {
        "data_out": {
            "required": True,
            "direction": "out",
            "local_path": "payload.tar",
            "recursive": False,
        },
    }

    def preprocess(self) -> None:
        """Immediately set job state to postprocessed to use Balsam's Globus transfer feature."""
        self.job.state = JobState.postprocessed

    @staticmethod
    def submit_remote_transfer(
        files: Iterable[Path], staging_dir: Path, destination: str, experiment_name: str
    ) -> Job:
        """Submit a remote transfer job.

        Stage `files` from persistent storage to `staging_dir`, then submit a
        TransferOut job to asynchronously manage the (Globus) stage-out to
        `destination`.

        Parameters
        ----------
        files : Iterable[Path]
            Files to transfer.
        staging_dir : Path
            Directory to stage tar transfer file to.
        destination : str
            Globus transfer destination of the form LOC:PATH.
        experiment_name : str
            Experiment name to tag transfer jobs with.

        Returns
        -------
        Job
            A Balsam Job object reference to the submitted transfer job.
        """
        transfer_id = str(uuid4())
        site_data_path = SiteConfig().data_path
        destination = destination.rstrip("/") + "/" + f"payload-{transfer_id}.tar"

        assert staging_dir.is_absolute()
        transfer_task_dir = staging_dir / f"{transfer_id}"
        transfer_task_dir.mkdir(parents=True)

        files = list(files)
        job_dir = files[0].parent
        file_string = " ".join(p.relative_to(job_dir).as_posix() for p in files)

        tar_file = transfer_task_dir / "payload.tar"
        p = subprocess.run(
            f"tar -cf {tar_file} -C {job_dir} {file_string}", shell=True, check=True
        )
        logger.debug(f"Tarred files for transfer to {destination} using: {p.args}")

        job = TransferOut.submit(
            workdir=transfer_task_dir.relative_to(site_data_path),
            transfers={"data_out": destination},
            tags={"experiment": experiment_name},
        )
        logger.info(f"Created TransferOut Job(id={job.id}, workdir={job.workdir})")
        return job


class TransferMethod(ABC):
    """Base class for transfer methods."""

    def __init__(self, transfer_config: TransferConfig, directory: Path) -> None:
        """Initialize a TransferMethod.

        Parameters
        ----------
        transfer_config : TransferConfig
            Configuration for the transfer method.
        directory : Path
            Directory to monitor and transfer files from.
        """
        self.patterns = transfer_config.patterns
        self.destination = transfer_config.destination
        self.poll_time = transfer_config.poll_time
        self.directory = directory
        self._seen_files: Set[Path] = set()

    def gather_unseen_files(self) -> Set[Path]:
        """Gather all files in `directory` that have not been seen before.

        Returns
        -------
        Set[Path]
            Set of files that have not been seen before.
        """
        all_files = {
            file for pattern in self.patterns for file in self.directory.glob(pattern)
        }
        unseen_files = all_files - self._seen_files
        self._seen_files.update(unseen_files)
        return unseen_files

    def run(self, exit_flag: Event) -> None:  # type: ignore[valid-type]
        """Run a daemon that periodically checks for new files to transfer.

        Parameters
        ----------
        exit_flag : Event
            Signals when to stop the daemon.
        """
        # Setup the transfer method
        self.pre_execute()

        # Loop until shutdown signal is set
        while not exit_flag.is_set():  # type: ignore[attr-defined]
            time.sleep(self.poll_time)
            self.transfer()

        # Transfer any extra files that appeared since the shutdown signal was set
        self.transfer()

    @abstractmethod
    def pre_execute(self) -> None:
        """Perform any pre-execution tasks in the process pool."""

    @abstractmethod
    def transfer(self) -> None:
        """Transfer files to the destination."""


class GlobusTransferMethod(TransferMethod):
    """Method for transfering files across sites."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        transfer_config: TransferConfig,
        directory: Path,
        staging_dir: Path,
        site_id: int,
        experiment_name: str,
    ) -> None:
        """Initialize a GlobusTransferMethod.

        The transfer daemon will submit async transfer Jobs to Balsam.
        The number of these is not bounded.

        Parameters
        ----------
        transfer_config : TransferConfig
            Configuration for the Globus transfer method.
        directory : Path
            Directory to monitor and transfer files from.
        staging_dir : Path
            Directory to stage files for transfer.
        site_id : int
            Balsam site ID to use for transfers.
        experiment_name : str
            Experiment name to tag transfer jobs with.
        """
        super().__init__(transfer_config, directory)
        self.staging_dir = staging_dir
        self.site_id = site_id
        self.experiment_name = experiment_name

    def pre_execute(self) -> None:
        """Set the current daemon process TransferOut site."""
        # TODO: See if this can be done once before the pool is started
        TransferOut.site = self.site_id

    def transfer(self) -> None:
        """Transfer files to a remote destination using Balsam/Globus."""
        assert isinstance(self.destination, str)
        files = self.gather_unseen_files()
        if files:
            logger.info(
                f"Submit TransferOut Job: stage {len(files)} files in "
                f"{self.staging_dir} for shipment out to {self.destination}"
            )
            TransferOut.submit_remote_transfer(
                files, self.staging_dir, self.destination, self.experiment_name
            )


class LocalCopyTransferMethod(TransferMethod):
    """Method for transfering files to a local directory."""

    def __init__(self, transfer_config: TransferConfig, directory: Path) -> None:
        """Initialize the local copy transfer method.

        Parameters
        ----------
        transfer_config : TransferConfig
            Configuration for the LocalCopy transfer method.
        directory : Path
            Directory to monitor and transfer files from.
        """
        super().__init__(transfer_config, directory)

    def pre_execute(self) -> None:
        """Do nothing."""

    def transfer(self) -> None:
        """Transfer files to a local directory."""
        files = self.gather_unseen_files()
        for src in files:
            logger.debug(f"shutil.copy {src.name} to {self.destination}")
            shutil.copy(src, self.destination)


class ShutDownCallback(ABC):  # pylint: disable=R0903
    """Abstract interface to define custom shutdown behavior."""

    @abstractmethod
    def check_shutdown(self) -> bool:
        """Logic to determine if the transfer should shut down.

        Returns
        -------
        bool
            True if the transfer service should shutdown, otherwise False.
        """


# TOOD: Need to test if the balsam job object id is identical
#       otherwise, may need to use the following function closure:
#       def shutdown_callback() -> bool:
#           # Closure on self.job, otherwise we would need to pass
#           # self.job to the run_job function
#           self.job.refresh_from_db()
#           shutdown: bool = self.job.data["shutdown"]
#           return shutdown


class JobSignalShutDownCallback(ShutDownCallback):  # pylint: disable=R0903
    """Custom shutdown callback that listens for a shutdown signal from the Balsam job."""

    def __init__(self, job: Job) -> None:
        """Initialize JobSignalShutDownCallback.

        Parameters
        ----------
        job : Job
            The balsam job object to monitor.
        """
        self.job = job

    def check_shutdown(self) -> bool:
        """Shutdown if the job metadata indicates that it should.

        Returns
        -------
        bool
            True if the job should be shutdown, False otherwise.
        """
        self.job.refresh_from_db()
        shutdown: bool = self.job.data["shutdown"]
        return shutdown


class TransferService:
    """Transfer service to manage transfers to remote and local locations."""

    def __init__(
        self,
        transfer_methods: List[TransferMethod],
        callbacks: Optional[List[ShutDownCallback]] = None,
    ) -> None:
        """Initialize a transfer service.

        Parameters
        ----------
        transfer_methods : List[TransferMethod]
            List of transfer methods to use.
        callbacks : List[ShutDownCallback], optional
            Optional list of callbacks to custumize shutdown behavior, by default []
        """
        self.exit_flag = Event()
        self.callbacks = [] if callbacks is None else callbacks
        self.daemons = self._start_remote_transfers(transfer_methods)

    def _start_remote_transfers(
        self, transfer_methods: List[TransferMethod]
    ) -> List[Process]:

        daemons = []
        for transfer_method in transfer_methods:
            proc = Process(
                target=transfer_method.run, daemon=True, args=(self.exit_flag,)
            )
            proc.start()
            daemons.append(proc)
        return daemons

    def check_shutdown(self) -> bool:
        """Check whether to shut down the transfer service.

        Returns
        -------
        bool
            Whether the service should shut down.
        """
        shutdown = False

        # Check if any of the daemons have shutdown
        if any(not d.is_alive() for d in self.daemons):
            logger.error("A transfer daemon failed! Aborting job.")
            shutdown = True

        # Check if any other callbacks want to shutdown
        if any(c.check_shutdown() for c in self.callbacks):
            logger.info("A callback requested a shutdown of the transfer service.")
            shutdown = True

        return shutdown

    def shutdown(self) -> None:
        """Shutdown the data transfer service."""
        # Give the signal for transfer daemons to exit
        self.exit_flag.set()
        logger.info("Shutting down transfer daemons...")
        for daemon in self.daemons:
            daemon.join()
        logger.info("Transfer daemons shut down.")
