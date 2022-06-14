"""Data transfer application."""
import itertools
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from balsam.api import ApplicationDefinition
from balsam.config import ClientSettings
from pydantic import BaseModel

from picoprobe.transfers import (
    GlobusTransferMethod,
    JobSignalShutDownCallback,
    LocalCopyTransferMethod,
    ShutDownCallback,
    TransferConfig,
    TransferMethod,
    TransferService,
)

logger = logging.getLogger(__name__)


class DataTransferConfig(BaseModel):
    """Configuration for DataTransferApplication."""

    root_scratch_dir: Path
    """The root scratch directory path."""
    transfer: TransferConfig
    """TransferConfig to specify destination."""


def run_job(transfer_service: TransferService) -> int:
    """Run a dummy job which sleeps.

    Parameters
    ----------
    transfer_service: TransferService
        Manages the transfer of data and determines when to shutdown.

    Returns
    -------
    int
        return code
    """
    for itr in itertools.count(0):
        logger.info("Check whether to shutdown")
        shutdown_ret = transfer_service.check_shutdown()
        logger.info(f"shutdown_callback ret: {shutdown_ret}")
        if shutdown_ret:
            # Trigger a shutdown event
            transfer_service.shutdown()
            return 0
        logger.info(f"Running iteration {itr}")
        time.sleep(10)
    return 1  # Should never get here


class DataTransferApplication(ApplicationDefinition):
    """Data transfer application."""

    site = "0"  # This attribute must be overritten in the child class

    def run(self, cfg_dict: Dict[str, Any]) -> None:  # type: ignore[override]
        """Run the data transfer application.

        Parameters
        ----------
        cfg_dict : Dict[str, Any]
            Configuration dictionary for RunConfig object.

        Raises
        ------
        RuntimeError
            If job fails.
        """
        cfg = DataTransferConfig(**cfg_dict)
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
        job_scratch_dir = cfg.root_scratch_dir / str(self.job.workdir)
        job_scratch_dir.mkdir(parents=True, exist_ok=True)

        transfer_methods: List[TransferMethod] = []
        if (
            isinstance(cfg.transfer.destination, str)
            and ":" in cfg.transfer.destination
        ):
            transfer_methods.append(
                GlobusTransferMethod(
                    transfer_config=cfg.transfer,
                    directory=job_scratch_dir,
                    staging_dir=transfer_staging_dir,
                    site_id=self.resolve_site_id(),
                    experiment_name=self.job.tags.get("experiment", "no-experiment"),
                )
            )
        else:
            assert isinstance(cfg.transfer.destination, Path)
            transfer_methods.append(
                LocalCopyTransferMethod(
                    transfer_config=cfg.transfer, directory=job_scratch_dir
                )
            )

        callbacks: List[ShutDownCallback] = [JobSignalShutDownCallback(self.job)]

        # TODO: Test if the JobSignalShutDownCallback is necessary for this application
        transfer_service = TransferService(transfer_methods, callbacks)

        return_code = run_job(transfer_service=transfer_service)

        if return_code != 0:
            raise RuntimeError(
                f"Error in job, please check output in: {job_persistent_dir}"
            )
