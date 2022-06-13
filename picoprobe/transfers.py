import logging
import shutil
import subprocess
import time
from multiprocessing import Event, Process
from pathlib import Path
from typing import Dict, Iterable, List, Set, Union
from uuid import uuid4

from balsam.api import ApplicationDefinition, Job
from balsam.config import SiteConfig
from balsam.schemas import JobState
from pydantic import BaseModel, validator


PathLike = Union[str, Path]

logger = logging.getLogger(__name__)


def run_untar_loop(
    input_directory: Path,
    untar_interval: float,
    expiration_time: float,
    max_concurrent_untars: int = 10,
) -> None:
    """
    Periodically untar incoming archives and clean up old .tar archives.
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
    poll_time: float = 10.0
    patterns: List[str]
    # TODO: destination should be type Union[str, Path], the
    #       str representation has a colon and is not PathLike.
    destination: PathLike

    @validator("destination")
    def destination_local_or_remote(cls, v: PathLike) -> PathLike:
        return str(v) if ":" in str(v) else Path(v)


class TransferOut(ApplicationDefinition):
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
        self.job.state = JobState.postprocessed

    @staticmethod
    def submit_remote_transfer(
        files: Iterable[Path], staging_dir: Path, destination: str, experiment_name: str
    ) -> Job:
        """
        Stage `files` from persistent storage to `staging_dir`, then submit a
        TransferOut job to asynchronously manage the (Globus) stage-out to
        `destination`.
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


def file_transfer_daemon(
    job_persistent_dir: Path,
    transfer_staging_dir: Path,
    transfer_poll_time: float,
    transfer_patterns: List[str],
    destination: Union[str, Path],
    site_id: int,
    experiment_name: str,
    exit_flag: Event,  # type: ignore[valid-type]
) -> None:
    """
    If `destination` is a Path, daemon will synchronously copy new files
    matching the `transfer_patterns` from `job_persistent_dir` to `destination`.
    If `destination` is a Balsam transfer string of the form
    "location_alias:path", the daemon will instead submit async transfer Jobs to
    Balsam.  The number of these is not bounded.
    """
    seen_files: Set[Path] = set()
    TransferOut.site = site_id

    # TODO: There is a small non-critical race condition where a new file
    #       matching pattern may be added to the persistent directory
    #       during the main transfer loop below, and then is not transfered
    #       if the exit_flag has been set (this would likely only happen)
    #       for the last output files of the simulation.
    while not exit_flag.is_set():  # type: ignore[attr-defined]
        time.sleep(transfer_poll_time)
        all_files = {
            file
            for pattern in transfer_patterns
            for file in job_persistent_dir.glob(pattern)
        }
        to_transfer = all_files - seen_files
        seen_files.update(to_transfer)

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


def start_remote_transfers(
    job_persistent_dir: Path,
    transfer_staging_dir: Path,
    transfer_cfgs: List[TransferDaemonConfig],
    site_id: int,
    experiment_name: str,
    exit_flag: Event,  # type: ignore[valid-type]
) -> List[Process]:

    daemons = []
    for cfg in transfer_cfgs:
        proc = Process(
            target=file_transfer_daemon,
            daemon=True,
            kwargs=dict(
                job_persistent_dir=job_persistent_dir,
                transfer_staging_dir=transfer_staging_dir,
                transfer_poll_time=cfg.poll_time,
                transfer_patterns=cfg.patterns,
                destination=cfg.destination,
                site_id=site_id,
                experiment_name=experiment_name,
                exit_flag=exit_flag,
            ),
        )
        proc.start()
        daemons.append(proc)
    return daemons
