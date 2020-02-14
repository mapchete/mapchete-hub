from collections import OrderedDict
import pytest

from mapchete_hub.api import load_mapchete_config, load_batch_config
from mapchete_hub.exceptions import JobNotFound


def test_api_get_capabilities(mhub_api):
    url = "/capabilities.json"
    response = mhub_api.get(url)
    assert response.status_code == 200
    assert response.json


def test_api_get_queues(mhub_api):
    url = "/queues"
    response = mhub_api.get(url)
    # TODO somehow the test client returns "308 Permanent Redirect"
    assert response.status_code == 308
    # assert response.json


# def test_api_get_queue_name(mhub_api):
#     url = "/queues/some_name"
#     response = mhub_api.get(url)
#     # TODO somehow the test client returns "308 Permanent Redirect"
#     assert response.status_code == 308
#     # assert response.json


def test_api_get_jobs(mhub_api):
    url = "/jobs/"
    response = mhub_api.get(url)
    assert response.status_code == 200
    assert len(response.json) == 0


def test_start_job(mhub_api, example_mapchete):
    job_id = "test"
    result = mhub_api.start_job(
        example_mapchete.path,
        job_id=job_id,
        bounds=example_mapchete.dict["bounds"],
        command="execute"
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


def test_start_batch(mhub_api, batch_example):
    result = mhub_api.start_batch(
        batch_example.path,
        bounds=[1, 2, 3, 4],
        command="execute"
    )
    assert result.status_code == 202


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
        for i in ["command", "mapchete_config", "zoom"]:
            assert i in params
    assert config["jobs"]["mosaic"]["zoom"] == 11
    assert config["jobs"]["overviews"]["zoom"] == [7, 10]
    assert config["jobs"]["indexes"]["zoom"] is None

    assert config["jobs"]["mosaic"]["mode"] == "continue"
    assert config["jobs"]["overviews"]["mode"] == "overwrite"
    assert config["jobs"]["indexes"]["mode"] == "continue"

    assert config["jobs"]["mosaic"]["queue"] is None
    assert config["jobs"]["overviews"]["queue"] == "overview_queue"
    assert config["jobs"]["indexes"]["queue"] is None

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
