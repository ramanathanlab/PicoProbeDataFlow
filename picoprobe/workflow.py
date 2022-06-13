import logging
import os
import time
import itertools
from pydantic import BaseModel
from multiprocessing import Event
from pathlib import Path
from typing import Any, Dict, List, Callable

from balsam.api import ApplicationDefinition
from balsam.config import ClientSettings

from transfers import start_remote_transfers, TransferDaemonConfig

logger = logging.getLogger(__name__)


class RunConfig(BaseModel):
    executable: str
    root_scratch_dir: Path

    transfer_daemons: List[TransferDaemonConfig] = []


def run_job(shutdown_callback: Callable[[], bool]) -> int:
    """Run a dummy job which sleeps.

    Parameters
    ----------
    shutdown_callback : Callable[[], bool]
        Function that returns True if the job should stop.
        Evaluated each iteration.

    Returns
    -------
    int
        return code
    """
    for itr in itertools.count(0):
        logger.info("Check shutdown_callback")
        shutdown_ret = shutdown_callback()
        logger.info(f"shutdown_callback ret: {shutdown_ret}")
        if shutdown_ret:
            # Trigger a shutdown event
            return 0
        logger.info(f"Running iteration {itr}")
        time.sleep(10)
    return 1  # Should never get here


class RunDataTransfer(ApplicationDefinition):

    site = "0"  # This attribute must be overritten in the child class

    def run(self, cfg_dict: Dict[str, Any]) -> None:  # type: ignore[override]
        cfg = RunConfig(**cfg_dict)
        client = ClientSettings.load_from_file().build_client()
        Site = client.Site
        site = Site.objects.get(id=self.resolve_site_id())

        # This is the Balsam Site's top-level /lustre/data/ dir
        site_data_dir = site.path / "data"

        # /lustre/to/data/experimentName/jobID
        job_persistent_dir = site_data_dir / self.job.workdir

        # /lustre/to/data/experimentName/transfer-staging
        transfer_staging_dir = job_persistent_dir.parent / "transfer-staging"
        transfer_staging_dir.mkdir(parents=True, exist_ok=True)

        # /node-local-SSD/scratch/experimentName/jobID
        if str(cfg.root_scratch_dir).startswith("$"):
            cfg.root_scratch_dir = Path(
                os.environ.get(
                    str(cfg.root_scratch_dir).lstrip("$"),
                    "/tmp",
                )
            )
            logger.info(
                f"Resolved root_scratch dir from environment: {cfg.root_scratch_dir}"
            )

        job_scratch_dir = cfg.root_scratch_dir / str(self.job.workdir)
        job_scratch_dir.mkdir(parents=True, exist_ok=True)

        exit_flag = Event()
        daemons = start_remote_transfers(
            job_persistent_dir,
            transfer_staging_dir,
            cfg.transfer_daemons,
            self.resolve_site_id(),
            self.job.tags.get("experiment", "no-experiment"),
            exit_flag,
        )

        def shutdown_callback() -> bool:
            # Closure on self.job, otherwise we would need to pass
            # self.job to the run_job function
            self.job.refresh_from_db()
            shutdown: bool = self.job.data["shutdown"]
            daemon_died = any(not d.is_alive() for d in daemons)
            if daemon_died:
                logger.error("A daemon failed! Aborting job with shutdown=True signal.")
                shutdown = True
            return shutdown

        return_code = run_job(shutdown_callback=shutdown_callback)

        if return_code != 0:
            raise RuntimeError(
                f"Error in job, please check output in: {job_persistent_dir}"
            )

        # Give the signal for transfer daemons to exit
        exit_flag.set()
        for daemon in daemons:
            daemon.join()
