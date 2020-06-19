"""mapchete_hub.api.API tests using the Flask pytest fixture."""


from collections import OrderedDict
import geojson
import pytest
from shapely.geometry import shape
import uuid

from mapchete_hub.api import format_as_geojson, load_mapchete_config, load_batch_config
from mapchete_hub.exceptions import JobNotFound, JobRejected


def test_api_get_capabilities(mhub_api):
    url = "/capabilities.json"
    response = mhub_api.get(url)
    assert response.status_code == 200
    assert response.json


def test_api_get_queues(mhub_api):
    url = "/queues"
    response = mhub_api.get(url)
    assert response.status_code == 200
    assert len(response.json) == 0


def test_api_get_queue_name(mhub_api):
    url = "/queues/some_name"
    response = mhub_api.get(url)
    assert response.status_code == 404
    assert "no queue found" in response.json["message"]


def test_api_get_jobs(mhub_api):
    url = "/jobs"
    response = mhub_api.get(url)
    assert response.status_code == 200
    assert len(response.json) == 0


def test_start_job(mhub_api, example_mapchete):
    job_id = uuid.uuid4().hex
    result = mhub_api.start_job(
        example_mapchete.path,
        job_id=job_id,
        bounds=example_mapchete.dict["bounds"],
        command="execute"
    )
    assert result.job_id == job_id

    # make sure job gets rejected if it has same ID
    with pytest.raises(JobRejected):
        mhub_api.start_job(
            example_mapchete.path,
            job_id=job_id,
            bounds=example_mapchete.dict["bounds"],
            command="execute"
        )

    # make sure wrong command raises an error
    with pytest.raises(ValueError):
        mhub_api.start_job(
            example_mapchete.path,
            job_id=job_id,
            bounds=example_mapchete.dict["bounds"],
            command="invalid"
        )


def test_cancel_job(mhub_api, example_mapchete):
    job_id = uuid.uuid4().hex

    # start job
    result = mhub_api.start_job(
        example_mapchete.path,
        job_id=job_id,
        bounds=example_mapchete.dict["bounds"],
        command="execute"
    )
    assert result.job_id == job_id

    # cancel job
    result = mhub_api.cancel_job(job_id)
    assert result.job_id == job_id
    assert result.status_code == 200
    assert "revoke signal" in result.json["message"]

    # make sure exception is raised if there is no job with this ID
    with pytest.raises(JobNotFound):
        mhub_api.cancel_job("unknown_job_id")


def test_start_batch(mhub_api, batch_example):
    job_id = uuid.uuid4().hex
    result = mhub_api.start_batch(
        batch_example.path,
        job_id=job_id,
        bounds=[1, 2, 3, 4],
        command="execute"
    )
    assert result.status_code == 202
    # make sure job gets rejected if it has same ID
    with pytest.raises(JobRejected):
        mhub_api.start_batch(
            batch_example.path,
            job_id=job_id,
            bounds=[1, 2, 3, 4],
            command="execute"
        )


def test_job(mhub_api):
    job_id = uuid.uuid4().hex
    with pytest.raises(JobNotFound):
        mhub_api.job(job_id)


def test_job_state(mhub_api):
    job_id = uuid.uuid4().hex
    with pytest.raises(JobNotFound):
        mhub_api.job_state(job_id)


def test_jobs(mhub_api):
    assert isinstance(mhub_api.jobs(), dict)


def test_jobs_states(mhub_api):
    assert isinstance(mhub_api.jobs_states(), dict)


def test_job_progress(mhub_api, example_mapchete):
    job_id = uuid.uuid4().hex
    with pytest.raises(JobNotFound):
        next(mhub_api.job_progress(job_id))

    job_id = uuid.uuid4().hex
    result = mhub_api.start_job(
        example_mapchete.path,
        job_id=job_id,
        bounds=example_mapchete.dict["bounds"],
        command="execute"
    )
    assert result.job_id == job_id

    with pytest.raises(TimeoutError):
        next(mhub_api.job_progress(job_id, timeout=2))


def test_format_as_geojson(response_json):
    # single feature
    gj = geojson.loads(format_as_geojson(response_json))
    for f in gj["features"]:
        assert "state" in f["properties"]
        assert shape(f["geometry"]).is_valid
    # multiple features
    gj = geojson.loads(format_as_geojson([response_json, response_json]))
    for f in gj["features"]:
        assert "state" in f["properties"]
        assert shape(f["geometry"]).is_valid


def test_load_mapchete_config(example_mapchete, example_custom_process_mapchete):
    # from path
    from_path = load_mapchete_config(example_mapchete.path)
    assert isinstance(from_path, OrderedDict)
    # from_dict
    from_dict = load_mapchete_config(OrderedDict(example_mapchete.dict))
    assert isinstance(from_dict, OrderedDict)
    with pytest.raises(TypeError):
        load_mapchete_config(example_mapchete.dict)
    # custom process function
    with_custom_process = load_mapchete_config(example_custom_process_mapchete.path)
    assert isinstance(with_custom_process, OrderedDict)


def test_load_batch_config(
    batch_example,
    batch_example_no_jobs_error,
    batch_example_invalid_job_pointer_error,
    batch_example_no_job_mapchete_error,
    batch_example_no_command_error
):
    config = load_batch_config(batch_example.path)

    assert isinstance(config, OrderedDict)
    assert "jobs" in config

    for job, params in config["jobs"].items():
        for i in ["command", "config", "params"]:
            assert i in params
    assert config["jobs"]["mosaic"]["params"]["zoom"] == 11
    assert config["jobs"]["overviews"]["params"]["zoom"] == [7, 10]
    assert config["jobs"]["indexes"]["params"]["zoom"] is None

    assert config["jobs"]["mosaic"]["params"]["mode"] == "continue"
    assert config["jobs"]["overviews"]["params"]["mode"] == "overwrite"
    assert config["jobs"]["indexes"]["params"]["mode"] == "continue"

    assert config["jobs"]["mosaic"]["params"]["queue"] is None
    assert config["jobs"]["overviews"]["params"]["queue"] == "overview_queue"
    assert config["jobs"]["indexes"]["params"]["queue"] is None

    # test errors
    with pytest.raises(FileNotFoundError):
        load_batch_config("not_existing_file.mhub")
    with pytest.raises(TypeError):
        load_batch_config("not_existing_file.mapchete")
    with pytest.raises(ValueError):
        load_batch_config(batch_example_no_jobs_error.path)
    with pytest.raises(ValueError):
        load_batch_config(batch_example_invalid_job_pointer_error.path)
    with pytest.raises(ValueError):
        load_batch_config(batch_example_no_job_mapchete_error.path)
    with pytest.raises(ValueError):
        load_batch_config(batch_example_no_command_error.path)
