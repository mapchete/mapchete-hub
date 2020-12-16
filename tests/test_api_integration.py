"""mapchete_hub.api.API tests using the full stack running under docker-compose."""

import pytest
import uuid

from mapchete_hub.exceptions import JobNotFound


def test_api_get_capabilities(wait_for_api, mhub_test_api):
    url = "/capabilities.json"
    response = mhub_test_api.get(url)
    assert response.status_code == 200
    assert response.json


def test_api_get_queues(wait_for_api, mhub_test_api):
    url = "/queues"
    response = mhub_test_api.get(url)
    assert response.status_code == 200
    assert len(response.json) == 3


def test_api_get_queue_name(wait_for_api, mhub_test_api):
    url = "/queues/execute_queue"
    response = mhub_test_api.get(url)
    assert response.status_code == 200
    assert "workers" in response.json


def test_api_get_jobs(wait_for_api, mhub_test_api):
    url = "/jobs"
    response = mhub_test_api.get(url)
    assert response.status_code == 200


def test_start_job(wait_for_api, example_mapchete, mhub_test_api):
    job_id = uuid.uuid4().hex
    result = mhub_test_api.start_job(
        example_mapchete.path,
        job_id=job_id,
        bounds=example_mapchete.dict["bounds"],
        command="execute"
    )
    assert result.job_id == job_id

    # get job progress
    for i in mhub_test_api.job_progress(job_id, interval=0.2):
        assert "state" in i


def test_cancel_job(wait_for_api, example_mapchete, mhub_test_api):
    job_id = uuid.uuid4().hex

    # start job
    result = mhub_test_api.start_job(
        example_mapchete.path,
        job_id=job_id,
        bounds=example_mapchete.dict["bounds"],
        command="execute"
    )
    assert result.job_id == job_id

    # cancel job
    result = mhub_test_api.cancel_job(job_id)
    assert result.job_id == job_id
    assert result.status_code == 200
    assert "Revoke signal" in result.json["message"]


def test_start_batch(wait_for_api, batch_example, mhub_test_api):
    result = mhub_test_api.start_batch(
        batch_example.path,
        bounds=[1, 2, 3, 4],
        command="execute"
    )
    assert result.status_code == 202


def test_job(wait_for_api, mhub_test_api):
    job_id = uuid.uuid4().hex
    with pytest.raises(JobNotFound):
        mhub_test_api.job(job_id)


def test_job_state(wait_for_api, mhub_test_api):
    job_id = uuid.uuid4().hex
    with pytest.raises(JobNotFound):
        mhub_test_api.job_state(job_id)


def test_jobs(wait_for_api, mhub_test_api):
    assert isinstance(mhub_test_api.jobs(), dict)


def test_jobs_states(wait_for_api, mhub_test_api):
    assert isinstance(mhub_test_api.jobs_states(), dict)


def test_job_progress(wait_for_api, example_mapchete, mhub_test_api):
    job_id = uuid.uuid4().hex
    with pytest.raises(JobNotFound):
        next(mhub_test_api.job_progress(job_id))

    job_id = uuid.uuid4().hex
    result = mhub_test_api.start_job(
        example_mapchete.path,
        job_id=job_id,
        bounds=example_mapchete.dict["bounds"],
        command="execute"
    )
    assert result.job_id == job_id

    with pytest.raises(TimeoutError):
        next(mhub_test_api.job_progress(job_id, timeout=2))
