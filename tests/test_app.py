import datetime
import json
import time

import pytest


def test_get_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()


def test_get_conformance(client):
    # TODO
    with pytest.raises(NotImplementedError):
        client.get("/conformance")


def test_get_dask_specs(client):
    response = client.get("/dask_specs")
    assert "default" in response.json()


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
        client.post(f"/processes/{test_process_id}")


def test_post_job(client, test_process_id, example_config_json):
    # response = client.get("/jobs")
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(
                    example_config_json["params"], zoom=2, dask_specs="s2_16bit_regular"
                ),
            )
        ),
    )
    assert response.status_code == 201
    assert client.get("/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = client.get(f"/jobs/{job_id}")
    all_jobs = client.get("/jobs/").json()
    assert len(all_jobs["features"]) == 1

    assert response.status_code == 200

    # make sure dask_specs were passed on
    assert response.json()["properties"]["dask_specs"]["worker_cores"] == 1


def test_post_job_custom_dask_specs(client, test_process_id, example_config_json):
    # response = client.get("/jobs")
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(
                    example_config_json["params"],
                    zoom=2,
                    dask_specs={"worker_threads": 8},
                ),
            )
        ),
    )
    assert response.status_code == 201
    assert client.get("/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200

    # make sure dask_specs were passed on
    assert response.json()["properties"]["dask_specs"].get("worker_threads") == 8


def test_post_job_custom_process(
    client, test_process_id, example_config_custom_process_json
):
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_custom_process_json,
                params=dict(example_config_custom_process_json["params"], zoom=2),
            )
        ),
    )
    assert response.status_code == 201
    assert client.get("/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["properties"]["status"] == "done"


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
                    params=dict(example_config_json["params"], zoom=2),
                )
            ),
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
                example_config_json, params=dict(example_config_json["params"], zoom=2)
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = client.get("/jobs", params={"bounds": "0,1,2,3"})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"bounds": "10,1,12,3"})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_list_jobs_area(client, test_process_id, example_config_json_area):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json_area,
                params=dict(example_config_json_area["params"], zoom=2),
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = client.get(
        "/jobs", params={"area": "Polygon ((0 1, 2 1, 2 3, 0 3, 0 1))"}
    )
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"bounds": "10,1,12,3"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_list_jobs_area_file(
    client, test_process_id, example_config_json_area_fgb, test_area_fgb
):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json_area_fgb,
                params=dict(example_config_json_area_fgb["params"], zoom=2),
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = client.get("/jobs", params={"area": test_area_fgb})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"bounds": "10,1,12,3"})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_list_jobs_bounds_area_file(
    client, test_process_id, example_config_json_area_fgb, test_area_fgb
):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json_area_fgb,
                params=dict(example_config_json_area_fgb["params"], zoom=2),
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = client.get("/jobs", params={"area": test_area_fgb, "bounds": "0,1,2,3"})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"bounds": "10,1,12,3"})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_list_jobs_output_path(client, test_process_id, example_config_json):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=2)
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = client.get(
        "/jobs", params={"output_path": example_config_json["config"]["output"]["path"]}
    )
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"output_path": "foo"})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_list_jobs_status(client, test_process_id, example_config_json):
    response = client.get("/jobs")
    assert response.status_code == 200
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=2)
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = client.get("/jobs", params={"status": "done"})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"status": "cancelled"})
    assert response.status_code == 200
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
                params=dict(example_config_json["params"], zoom=2, job_name="foo"),
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    response = client.get("/jobs", params={"job_name": "foo"})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = client.get("/jobs", params={"job_name": "bar"})
    assert response.status_code == 200
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
                example_config_json, params=dict(example_config_json["params"], zoom=2)
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    now = datetime.datetime.utcfromtimestamp(time.time()).strftime("%Y-%m-%dT%H:%M:%SZ")
    response = client.get("/jobs", params={"from_date": now})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    future = datetime.datetime.utcfromtimestamp(time.time() + 60).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    response = client.get("/jobs", params={"from_date": future})
    assert response.status_code == 200
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
                example_config_json, params=dict(example_config_json["params"], zoom=2)
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    now = datetime.datetime.utcfromtimestamp(time.time() + 60).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    response = client.get("/jobs", params={"to_date": now})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    past = datetime.datetime.utcfromtimestamp(time.time() - 60).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    response = client.get("/jobs", params={"to_date": past})
    assert response.status_code == 200
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


def test_send_cancel_signal(client, test_process_id, example_config_json):
    """The background task does not run in the background in TestClient, therefore we can only test the request."""
    # make one long running job
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=2)
            )
        ),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    # send cancel signal
    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200


def test_job_result(client, test_process_id, example_config_json):
    result = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=2)
            )
        ),
    )
    job_id = result.json()["id"]

    result = client.get(f"/jobs/{job_id}/results")
    assert result.status_code == 200
    assert isinstance(result.json(), dict)
    assert "tmp" in result.json()["imagesOutput"]["href"]


def test_errors(client, example_config_json):
    # get job
    response = client.get("/jobs/foo")
    assert response.status_code == 404

    # cancel job
    response = client.delete("/jobs/foo")
    assert response.status_code == 404

    # get job results
    response = client.get("/jobs/foo/results")
    assert response.status_code == 404


def test_process_exception(
    client, test_process_id, example_config_process_exception_json
):
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(example_config_process_exception_json),
    )
    assert response.status_code == 201
    job_id = response.json()["id"]

    # make sure job failed
    response = client.get(f"/jobs/{job_id}")
    assert response.json()["properties"]["status"] == "failed"
    assert response.json()["properties"]["traceback"]

    # make sure <job_id>/results shows an exception
    response = client.get(f"/jobs/{job_id}/results")
    assert response.status_code == 400
    # NOTE: we need to raise MapcheteTaskFailed errors again in the core package
    # assert response.json()["detail"]["properties"]["type"].startswith(
    #     "MapcheteTaskFailed"
    # )
    assert "ZeroDivisionError" in response.json()["detail"]["properties"]["type"]
    assert isinstance(response.json()["detail"]["properties"]["detail"], str)


def test_process_custom_params(client, test_process_id, example_config_json):
    conf = dict(example_config_json)
    conf["config"]["process_parameters"] = dict(foo="bar")
    response = client.post(
        f"/processes/{test_process_id}/execution", data=json.dumps(conf)
    )
    job_id = response.json()["id"]

    # make sure custom parameter was passed on
    response = client.get(f"/jobs/{job_id}")
    assert (
        "foo"
        in response.json()["properties"]["mapchete"]["config"]["process_parameters"]
    )


def test_dask_dashboard_link(client, test_process_id, example_config_json):
    response = client.post(
        f"/processes/{test_process_id}/execution", data=json.dumps(example_config_json)
    )
    job_id = response.json()["id"]

    # make sure custom parameter was passed on
    response = client.get(f"/jobs/{job_id}")
    assert response.json()["properties"].get("dask_dashboard_link")
