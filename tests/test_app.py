import datetime
import json
import pytest
import time


def test_get_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()


def test_get_conformance(client):
    # TODO
    with pytest.raises(NotImplementedError):
        response = client.get("/conformance")


def test_get_processes(client):
    response = client.get("/processes")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_get_process(client):
    response = client.get("/processes/mapchete.processes.convert")
    assert response.status_code == 200
    assert "title" in response.json()

    response = client.get("/processes/invalid_process")
    assert response.status_code == 404


def test_post_process(client, test_process_id):
    # TODO
    with pytest.raises(NotImplementedError):
        response = client.post(f"/processes/{test_process_id}")


def test_post_job(client, test_process_id, example_config_json):
    # response = client.get("/jobs")
    response = client.post(
        f"/processes/{test_process_id}/execution",
            data=json.dumps(
                dict(
                    example_config_json,
                    params=dict(example_config_json["params"], zoom=2)
                )
            )
    )
    assert response.status_code == 201
    assert client.get("/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200


def test_post_job_custom_process(client, test_process_id, example_config_custom_process_json):
    response = client.post(
        f"/processes/{test_process_id}/execution",
            data=json.dumps(
                dict(
                    example_config_custom_process_json,
                    params=dict(example_config_custom_process_json["params"], zoom=2)
                )
            )
    )
    assert response.status_code == 201
    assert client.get("/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["properties"]["state"] == "done"


def test_list_jobs(client, test_process_id, example_config_json):
    # this should be empty
    response = client.get("/jobs")
    assert response.status_code == 200
    before = len(response.json()["features"])

    # make two short running jobs
    for _ in range(2):
        client.post(
            f"/processes/{test_process_id}/execution",
            data=json.dumps(
                dict(
                    example_config_json,
                    params=dict(example_config_json["params"], zoom=2)
                )
            )
        )

    response = client.get("/jobs")
    assert response.status_code == 200
    after = len(response.json()["features"])
    assert after > before


def test_list_jobs_bounds(client, test_process_id, example_config_json):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2)
            )
        )
    )
    job_id = response.json()["id"]

    # NotImplementedError: '$geoIntersects' is a valid operation but it is not supported by Mongomock yet.
    with pytest.raises(NotImplementedError):
        response = client.get("/jobs", params={"bounds": "0,1,2,3"})
        jobs = [j["id"] for j in response.json()["features"]]
        assert job_id in jobs
    with pytest.raises(NotImplementedError):
        response = client.get("/jobs", params={"bounds": "10,1,12,3"})
        jobs = [j["id"] for j in response.json()["features"]]
        assert job_id not in jobs


def test_list_jobs_output_path(client, test_process_id, example_config_json):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2)
            )
        )
    )
    job_id = response.json()["id"]

    response = client.get("/jobs", params={"output_path": example_config_json["config"]["output"]["path"]})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"output_path": "foo"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_list_jobs_state(client, test_process_id, example_config_json):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2)
            )
        )
    )
    job_id = response.json()["id"]

    response = client.get("/jobs", params={"state": "done"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"state": "cancelled"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_list_jobs_job_name(client, test_process_id, example_config_json):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2, job_name="foo")
            )
        )
    )
    job_id = response.json()["id"]

    response = client.get("/jobs", params={"job_name": "foo"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"job_name": "bar"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


# @pytest.mark.skip(reason="mongomock does not seem to handle $lte and $gte operators correctly")
def test_list_jobs_from_date(client, test_process_id, example_config_json):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2)
            )
        )
    )
    job_id = response.json()["id"]

    now = datetime.datetime.utcfromtimestamp(time.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = client.get("/jobs", params={"from_date": now})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    future = datetime.datetime.utcfromtimestamp(time.time() + 60).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = client.get("/jobs", params={"from_date": future})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


# @pytest.mark.skip(reason="mongomock does not seem to handle $lte and $gte operators correctly")
def test_list_jobs_to_date(client, test_process_id, example_config_json):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2)
            )
        )
    )
    job_id = response.json()["id"]

    now = datetime.datetime.utcfromtimestamp(time.time() + 60).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = client.get("/jobs", params={"to_date": now})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    past = datetime.datetime.utcfromtimestamp(time.time() - 60).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = client.get("/jobs", params={"to_date": past})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_send_cancel_signal(client, test_process_id, example_config_json):
    """The background task does not run in the background in TestClient, therefore we can only test the request."""
    # make one long running job
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2)
            )
        )
    )
    job_id = response.json()["id"]

    # # make sure job is running
    # response = client.get(f"/jobs/{job_id}")
    # assert response.json()["properties"]["state"] == "running"

    # send cancel signal
    response = client.delete(f"/jobs/{job_id}")

    # response = client.get(f"/jobs/{job_id}")
    # assert response.json()["properties"]["state"] == "aborting"


def test_job_result(client, test_process_id, example_config_json):
    result = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2)
            )
        )
    )
    job_id = result.json()["id"]

    result = client.get(f"/jobs/{job_id}/result")
    assert result.status_code == 200
    assert "tmp" in result.json()


def test_errors(client, example_config_json):
    # get job
    response = client.get(f"/jobs/foo")
    assert response.status_code == 404

    # cancel job
    response = client.delete(f"/jobs/foo")
    assert response.status_code == 404

    # get job result
    response = client.get(f"/jobs/foo/result")
    assert response.status_code == 404


def test_process_exception(client, test_process_id, example_config_process_exception_json):
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(example_config_process_exception_json)
    )
    job_id = response.json()["id"]

    # make sure job failed
    response = client.get(f"/jobs/{job_id}")
    assert response.json()["properties"]["state"] == "failed"
    assert response.json()["properties"]["traceback"]


def test_process_custom_params(client, test_process_id, example_config_json):
    conf = dict(example_config_json)
    conf["config"].update(foo="bar")
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(conf)
    )
    job_id = response.json()["id"]

    # make sure custom parameter was passed on
    response = client.get(f"/jobs/{job_id}")
    assert "foo" in response.json()["properties"]["mapchete"]["config"]
