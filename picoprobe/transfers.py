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
            p = subprocess.Popen(
                f"tar -xvf {tar_file.name}", cwd=input_directory, shell=True
            )
            processes.append(p)
            tar_file_ages[tar_file] = 0.0

        # Only remove tar files that have been around for the expiration_time
        to_remove = [f for f, age in tar_file_ages.items() if age >= expiration_time]
        for f in to_remove:
            f.unlink()
            tar_file_ages.pop(f)


class TransferDaemonConfig(BaseModel):
    """Configuration for a data transfer daemon."""

    poll_time: float = 10.0
    """Number of seconds between polling for new files to transfer."""
    patterns: List[str]
    """List of glob patterns to match files to transfer."""
    # TODO: destination should be type Union[str, Path], the
    #       str representation has a colon and is not PathLike.
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
        p = subprocess.run(f"tar -cf {tar_file} -C {job_dir} {file_string}", shell=True)
        logger.debug(f"Tarred files for transfer to {destination} using: {p.args}")

        job = TransferOut.submit(
            workdir=transfer_task_dir.relative_to(site_data_path),
            transfers={"data_out": destination},
            tags={"experiment": experiment_name},
        )
        logger.info(f"Created TransferOut Job(id={job.id}, workdir={job.workdir})")
        return job


class FileManager:
    """Manage files to be transferred."""

    def __init__(self, directory: Path, patterns: List[str]) -> None:
        """Initialize a FileManager to gather files from `directory` matching glob `patterns`.

        Parameters
        ----------
        directory : Path
            Directory to gather files from.
        patterns : List[str]
            List of glob patterns to match files.
        """
        self.directory = directory
        self.patterns = patterns
        self.seen_files: Set[Path] = set()

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
        unseen_files = all_files - self.seen_files
        self.seen_files.update(unseen_files)
        return unseen_files


def _file_transfer_daemon(
    job_persistent_dir: Path,
    transfer_staging_dir: Path,
    transfer_poll_time: float,
    transfer_patterns: List[str],
    destination: Union[str, Path],
    site_id: int,
    experiment_name: str,
    exit_flag: Event,  # type: ignore[valid-type]
) -> None:
    """Run a daemon that periodically checks for new files to transfer.

    If `destination` is a Path, daemon will synchronously copy new files
    matching the `transfer_patterns` from `job_persistent_dir` to `destination`.
    If `destination` is a Balsam transfer string of the form
    "location_alias:path", the daemon will instead submit async transfer Jobs to
    Balsam. The number of these is not bounded.

    Parameters
    ----------
    job_persistent_dir : Path
        Persistent directory for job output files.
    transfer_staging_dir : Path
        Directory to stage files for transfer.
    transfer_poll_time : float
        Number of seconds between polling for new files to transfer.
    transfer_patterns : List[str]
        File pattern to glob for new files to transfer in `job_persistent_dir`.
    destination : Union[str, Path]
        Where to transfer files to. Must be either Balsam LOC:PATH string or a local Path.
    site_id : int
        Balsam site ID to use for transfers.
    experiment_name : str
        Experiment name to tag transfer jobs with.
    exit_flag : Event
        Signals when to stop the daemon.

    Raises
    ------
    ValueError
        If `destination` is invalid
    """
    # Set the current daemon process TransferOut site
    TransferOut.site = site_id

    # Create a FileManager to collect files to transfer
    file_manager = FileManager(job_persistent_dir, transfer_patterns)

    # TODO: There is a small non-critical race condition where a new file
    #       matching pattern may be added to the persistent directory
    #       during the main transfer loop below, and then is not transfered
    #       if the exit_flag has been set (this would likely only happen)
    #       for the last output files of the simulation.
    while not exit_flag.is_set():  # type: ignore[attr-defined]
        time.sleep(transfer_poll_time)
        to_transfer = file_manager.gather_unseen_files()
        # If there are no new files, don't submit a new transfer job
        if not to_transfer:
            continue

        # Transfer with Balsam Transfer
        if isinstance(destination, str) and ":" in destination:
            if to_transfer:
                logger.debug(
                    f"Submit TransferOut Job: stage {len(to_transfer)} files in {transfer_staging_dir} for shipment out to {destination}"
                )
                TransferOut.submit_remote_transfer(
                    to_transfer,
                    transfer_staging_dir,
                    destination,
                    experiment_name,
                )

        # Transfer to local filesystem
        elif isinstance(destination, Path):
            for src in to_transfer:
                logger.debug(f"shutil.copy {src.name} to {destination}")
                shutil.copy(src, destination)

        else:
            raise ValueError(
                f"Invalid `destination`: {destination} ... Must be either Balsam LOC:PATH string or a local Path."
            )


class ShutDownCallback(ABC):
    """Abstract interface to define custom shutdown behavior."""

    @abstractmethod
    def check_shutdown(self) -> bool:
        """Logic to determine if the transfer should shut down.

        Returns
        -------
        bool
            True if the transfer service should shutdown, otherwise False.
        """
        pass


# TOOD: Need to test if the balsam job object id is identical
#       otherwise, may need to use the following function closure:
#       def shutdown_callback() -> bool:
#           # Closure on self.job, otherwise we would need to pass
#           # self.job to the run_job function
#           self.job.refresh_from_db()
#           shutdown: bool = self.job.data["shutdown"]
#           return shutdown


class JobSignalShutDownCallback(ShutDownCallback):
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
        job_persistent_dir: Path,
        transfer_staging_dir: Path,
        transfer_cfgs: List[TransferDaemonConfig],
        site_id: int,
        experiment_name: str,
        callbacks: Optional[List[ShutDownCallback]] = None,
    ) -> None:
        """Initialize a transfer service.

        Parameters
        ----------
        job_persistent_dir : Path
            Persistent directory for job output files.
        transfer_staging_dir : Path
            Directory to stage files for transfer.
        transfer_cfgs : List[TransferDaemonConfig]
            Configuration for transfer daemons.
        site_id : int
            Balsam site ID to use for transfers.
        experiment_name : str
            Experiment name to tag transfer jobs with.
        callbacks : List[ShutDownCallback], optional
            Optional list of callbacks to custumize shutdown behavior, by default []
        """
        self.exit_flag = Event()
        # TODO: Is it possible to combine job_persistent_dir and transfer_staging_dir?
        self.daemons = self._start_remote_transfers(
            job_persistent_dir,
            transfer_staging_dir,
            transfer_cfgs,
            site_id,
            experiment_name,
        )

        self.callbacks = [] if callbacks is None else callbacks

    def _start_remote_transfers(
        self,
        job_persistent_dir: Path,
        transfer_staging_dir: Path,
        transfer_cfgs: List[TransferDaemonConfig],
        site_id: int,
        experiment_name: str,
    ) -> List[Process]:

        daemons = []
        for cfg in transfer_cfgs:
            proc = Process(
                target=_file_transfer_daemon,
                daemon=True,
                kwargs=dict(
                    job_persistent_dir=job_persistent_dir,
                    transfer_staging_dir=transfer_staging_dir,
                    transfer_poll_time=cfg.poll_time,
                    transfer_patterns=cfg.patterns,
                    destination=cfg.destination,
                    site_id=site_id,
                    experiment_name=experiment_name,
                    exit_flag=self.exit_flag,
                ),
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
