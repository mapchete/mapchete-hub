import datetime
import pytest
from shapely.geometry import shape
import time

from mapchete_hub import models
from mapchete_hub.db import BackendDB
from mapchete_hub.geometry import process_area_from_config


def test_mongodb_backend_job(example_config_json, mongodb):
    job_config = models.MapcheteJob(**example_config_json)
    with BackendDB(src=mongodb) as db:
        # add new job
        job = db.new(job_config=job_config)

        job_id = job['id']

        current = db.job(job_id)
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        assert list(geom.bounds) == current["bounds"]

        # write pending event
        db.set(job_id, state="pending")
        current = db.job(job_id)
        assert current["properties"]["state"] == "pending"
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        # write initializing event
        db.set(job_id, state="created")
        current = db.job(job_id)
        assert current["properties"]["state"] == "created"
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        # write initializing event
        db.set(job_id, state="initializing")
        current = db.job(job_id)
        assert current["properties"]["state"] == "initializing"
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        # write initialized event
        db.set(job_id, state="initialized")
        current = db.job(job_id)
        assert current["properties"]["state"] == "initialized"
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        # write running event
        db.set(job_id, state="running", current_progress=0, total_progress=100)
        current = db.job(job_id)
        assert current["properties"]["state"] == "running"
        assert current["properties"]["current_progress"] == 0
        assert current["properties"]["total_progress"] == 100
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        # update job progress
        db.set(job_id, current_progress=50)
        current = db.job(job_id)
        assert current["properties"]["state"] == "running"
        assert current["properties"]["current_progress"] == 50
        assert current["properties"]["total_progress"] == 100
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        # write done event
        db.set(job_id, state="done")
        current = db.job(job_id)
        assert current["properties"]["state"] == "done"
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        # write fail event
        db.set(job_id, state="failed", exception=ZeroDivisionError)
        current = db.job(job_id)
        assert current["properties"]["state"] == "failed"
        assert "ZeroDivisionError" in current["properties"]["exception"]
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        # write another job
        another_job = db.new(job_config=job_config)
        another_job_id = another_job["id"]
        current = db.job(another_job_id)
        geom = shape(current["geometry"])
        assert geom.is_valid
        assert not geom.is_empty

        db.set(another_job_id, state="pending")
        all_jobs = db.jobs()

        certain_jobs = db.jobs(state=["pending", "failed"])
        assert len(certain_jobs) == 2

        assert len(all_jobs) == 2

        # filter by time
        future = datetime.datetime.utcfromtimestamp(time.time() + 60)
        assert len(db.jobs(from_date=future)) == 0
        assert len(db.jobs(to_date=future)) == 2
        past = datetime.datetime.utcfromtimestamp(time.time() - 60)
        assert len(db.jobs(from_date=past)) == 2
        assert len(db.jobs(to_date=past)) == 0

        # filter by state
        assert len(db.jobs(state="done")) == 0
        assert len(db.jobs(state="failed")) == 1
        assert len(db.jobs(state="pending")) == 1

        # filter by output path
        # assert len(db.jobs(output_path="/tmp/test/")) == 2

        # filter by command
        assert len(db.jobs(command="execute")) == 2

        # filter by bounds
        # '$geoIntersects' is a valid operation but it is not supported by Mongomock yet.
        with pytest.raises(NotImplementedError):
            assert len(db.jobs(bounds=[1, 2, 3, 4])) == 2
        with pytest.raises(NotImplementedError):
            assert len(db.jobs(bounds=[11, 12, 13, 14])) == 0
