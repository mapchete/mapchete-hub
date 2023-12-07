import datetime
from mapchete.enums import Status
from mapchete.types import Progress
import pytest
from shapely.geometry import shape
import time

from mapchete_hub import models
from mapchete_hub.db import init_backenddb


@pytest.mark.parametrize("backend_db", ["mongodb", "memory"])
def test_mongodb_backend_job(example_config_json, backend_db, mongodb):
    job_config = models.MapcheteJob(**example_config_json)
    with init_backenddb(src=mongodb if backend_db == "mongodb" else "memory") as db:
        # add new job
        job = db.new(job_config=job_config)

        job_id = job.job_id

        current = db.job(job_id)
        geom = shape(current)
        assert geom.is_valid
        assert not geom.is_empty

        assert list(geom.bounds) == current.bounds

        # write parsing event
        db.set(job_id, status="parsing")
        current = db.job(job_id)
        assert current.status == Status.parsing
        geom = shape(current)
        assert geom.is_valid
        assert not geom.is_empty

        # write initializing event
        db.set(job_id, status="initializing")
        current = db.job(job_id)
        assert current.status == Status.initializing
        geom = shape(current)
        assert geom.is_valid
        assert not geom.is_empty

        # write running event
        db.set(job_id, status="running", progress=Progress(current=0, total=100))
        current = db.job(job_id)
        assert current.status == Status.running
        assert current.current_progress == 0
        assert current.total_progress == 100
        geom = shape(current)
        assert geom.is_valid
        assert not geom.is_empty

        # update job progress
        db.set(job_id, progress=Progress(current=50))
        current = db.job(job_id)
        assert current.status == Status.running
        assert current.current_progress == 50
        assert current.total_progress == 100
        geom = shape(current)
        assert geom.is_valid
        assert not geom.is_empty

        # write done event
        db.set(job_id, status="done")
        current = db.job(job_id)
        assert current.status == Status.done
        geom = shape(current)
        assert geom.is_valid
        assert not geom.is_empty

        # write fail event
        db.set(job_id, status="failed", exception=ZeroDivisionError)
        current = db.job(job_id)
        assert current.status == Status.failed
        assert "ZeroDivisionError" in current.exception
        geom = shape(current)
        assert geom.is_valid
        assert not geom.is_empty

        # write another job
        another_job = db.new(job_config=job_config)
        another_job_id = another_job.job_id
        current = db.job(another_job_id)
        geom = shape(current)
        assert geom.is_valid
        assert not geom.is_empty

        db.set(another_job_id, status="parsing")
        all_jobs = db.jobs()

        certain_jobs = db.jobs(status=["parsing", "failed"])
        assert len(certain_jobs) == 2

        assert len(all_jobs) == 2

        # filter by time
        future = datetime.datetime.utcfromtimestamp(time.time() + 60)
        assert len(db.jobs(from_date=future)) == 0
        assert len(db.jobs(to_date=future)) == 2
        past = datetime.datetime.utcfromtimestamp(time.time() - 60)
        assert len(db.jobs(from_date=past)) == 2
        assert len(db.jobs(to_date=past)) == 0

        # filter by status
        assert len(db.jobs(status="done")) == 0
        assert len(db.jobs(status="failed")) == 1
        assert len(db.jobs(status="parsing")) == 1

        # filter by output path
        # assert len(db.jobs(output_path="/tmp/test/")) == 2

        # filter by command
        assert len(db.jobs(command="execute")) == 2

        # filter by bounds
        # '$geoIntersects' is a valid operation but it is not supported by Mongomock yet.
        if backend_db == "mongodb":
            with pytest.raises(NotImplementedError):
                assert len(db.jobs(bounds=[1, 2, 3, 4])) == 2
            with pytest.raises(NotImplementedError):
                assert len(db.jobs(bounds=[11, 12, 13, 14])) == 0
        else:
            assert len(db.jobs(bounds=[1, 2, 3, 4])) == 2
            assert len(db.jobs(bounds=[11, 12, 13, 14])) == 0
