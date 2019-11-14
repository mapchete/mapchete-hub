import pytest

from mapchete_hub.exceptions import JobNotFound


def test_api_get(mhub_api):
    url = "/jobs/"
    response = mhub_api.get(url)
    assert response.status_code == 200
    assert len(response.json) == 0


def test_start_job(mhub_api, example_mapchete):
    job_id = "test"
    result = mhub_api.start_job(
        example_mapchete.path,
        job_id=job_id,
        bounds=example_mapchete.dict["bounds"]
    )
    assert result.job_id == job_id
    # url = "/jobs/%s" % job_id
    # config = dict(example_mapchete.dict)
    # # config.pop("mhub_next_process")

    # data = mapchete_hub.cleanup_datetime(
    #     dict(
    #         mapchete_config=config,
    #         zoom=11,
    #         point=None,
    #         wkt_geometry=None,
    #         tile=(11, 244, 517),
    #         mode="continue"
    #     )
    # )
    # response = api_client.post(url, json=data, _client=client)
    # assert response.status_code == 202
    # assert "geometry" in response.json
    # assert "properties" in response.json
    # assert response.json["properties"]["state"] == "PENDING"


def test_job(mhub_api):
    job_id = "test"
    with pytest.raises(JobNotFound):
        mhub_api.job(job_id)


def test_job_state(mhub_api):
    job_id = "test"
    with pytest.raises(JobNotFound):
        mhub_api.job_state(job_id)


def test_jobs(mhub_api):
    assert isinstance(mhub_api.jobs(), dict)


def test_jobs_states(mhub_api):
    assert isinstance(mhub_api.jobs_states(), dict)


def test_job_progress(mhub_api):
    job_id = "test"
    with pytest.raises(JobNotFound):
        next(mhub_api.job_progress(job_id))
