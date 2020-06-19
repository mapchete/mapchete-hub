import pytest
from shapely.geometry import shape

from mapchete_hub.db import BackendDB


def test_mongodb_backend(
    new_job_metadata,
    event_pending,
    event_progress,
    event_success,
    event_failure,
    mongodb
):
    test_job = event_pending["uuid"]
    another_test_job = "another_test_job"

    another_pending = dict(event_pending, uuid=another_test_job)

    with BackendDB(src=mongodb) as status_w:
        with BackendDB(src=mongodb) as status_r:
            # add new job
            status_w.new(job_id=test_job, metadata=new_job_metadata)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty

            # write pending event
            status_w.update(test_job, event_pending)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty

            # write progress event
            status_w.update(test_job, event_progress)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty

            # write success event
            status_w.update(test_job, event_success)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty

            # write fail event
            status_w.update(test_job, event_failure)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty

            # write another job
            status_w.new(
                job_id=another_test_job,
                metadata=dict(new_job_metadata, job_id=another_test_job)
            )
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty

            status_w.update(another_test_job, another_pending)
            all_jobs = status_r.jobs()
            assert len(all_jobs) == 2

            # TODO: filter by time

            # filter by state
            assert len(status_r.jobs(state="SUCCESS")) == 0
            assert len(status_r.jobs(state="FAILURE")) == 1
            assert len(status_r.jobs(state="done")) == 1
            assert len(status_r.jobs(state="PENDING")) == 1
            assert len(status_r.jobs(state="todo")) == 1

            # filter by output path
            assert len(status_r.jobs(output_path="test")) == 2

            # filter by command
            assert len(status_r.jobs(command="execute")) == 2

            # filter by queue
            assert len(status_r.jobs(queue="execute_queue")) == 0

            # filter by bounds
            # '$geoIntersects' is a valid operation but it is not supported by Mongomock yet.
            with pytest.raises(NotImplementedError):
                assert len(status_r.jobs(bounds=[1, 2, 3, 4])) == 2
            with pytest.raises(NotImplementedError):
                assert len(status_r.jobs(bounds=[11, 12, 13, 14])) == 0

            # filter by job_name
            assert len(status_r.jobs(job_name="unnamed_job")) == 0
