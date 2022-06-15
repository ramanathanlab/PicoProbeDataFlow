import time
from typing import Optional
from balsam.api import Job, BatchJob
from pathlib import Path
from picoprobe.transfers import TransferConfig
from picoprobe.workflow import DataTransferApplication, DataTransferConfig


class LocalDataTransferApplication(DataTransferApplication):
    site = "my-laptop"
    python_exe = "/Users/abrace/src/PicoProbeDataFlow/env/bin/python3"


class ThetaDataTransferApplication(DataTransferApplication):
    site = "thetagpu-picoprobe"
    python_exe = "TODO"


class Application:
    def __init__(self, experiment_name: str, cfg: DataTransferConfig) -> None:
        self.experiment_name = experiment_name
        self.cfg = cfg

        self.job: Optional[Job] = None

    def shutdown(self) -> None:
        if self.job is not None:
            self.job.data = {"shutdown": True}
            self.job.save()

    def run(self) -> None:
        self.job = ThetaDataTransferApplication.submit(
            workdir=Path(self.experiment_name),
            data={"shutdown": False},
            tags={"experiment": self.experiment_name},
            cfg_dict=self.cfg.dict(),
        )
        BatchJob.objects.create(
            site_id=self.job.site_id,
            num_nodes=1,
            wall_time_min=60,
            job_mode="mpi",
            project="RL-fold",
            queue="single-gpu",
            filter_tags={"experiment": self.experiment_name},
        )
        while True:
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                print("Shutting down")
                self.shutdown()
                break


if __name__ == "__main__":

    ThetaDataTransferApplication.sync()

    experiment_name = "test-experiment"
    experiment_dir = Path(
        "/Users/abrace/src/PicoProbeDataFlow/examples/test-experiment"
    )
    cfg = DataTransferConfig(
        root_scratch_dir=experiment_dir / "source",
        transfer=TransferConfig(
            poll_time=10,
            patterns=["*.txt"],
            destination=experiment_dir / "dst",
        ),
    )

    app = Application(experiment_name, cfg)
    app.run()
