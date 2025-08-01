import datetime
import json
import os
import time

import pytest
import requests

from mapchete_hub.timetools import date_to_str

TEST_ENDPOINT = os.environ.get("MHUB_HOST", "http://0.0.0.0:5000")


def _endpoint_available():
    try:
        response = requests.get(TEST_ENDPOINT)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


ENDPOINT_AVAILABLE = _endpoint_available()


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using either 'docker-compose up' or 'mhub-server start'",
)
def test_get_root():
    response = requests.get(f"{TEST_ENDPOINT}/")
    assert response.status_code == 200
    assert response.json()


# @pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
# def test_get_conformance():
#     # TODO
#     with pytest.raises(NotImplementedError):
#         response = requests.get(f"{TEST_ENDPOINT}/conformance")


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_get_processes():
    response = requests.get(f"{TEST_ENDPOINT}/processes")
    assert response.status_code == 200
    assert len(response.json()) > 0


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_get_process():
    response = requests.get(f"{TEST_ENDPOINT}/processes/mapchete.processes.convert")
    assert response.status_code == 200
    assert "title" in response.json()

    response = requests.get(f"{TEST_ENDPOINT}/processes/invalid_process")
    assert response.status_code == 404


# @pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
# def test_post_process(test_process_id):
#     # TODO
#     with pytest.raises(NotImplementedError):
#         response = requests.post(f"{TEST_ENDPOINT}/processes/{test_process_id}")


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_post_job(test_process_id, example_config_json):
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(example_config_json),
    )
    assert response.status_code == 201

    assert requests.get(f"{TEST_ENDPOINT}/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.status_code == 200


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_post_job_custom_process(test_process_id, example_config_custom_process_json):
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(example_config_custom_process_json),
    )
    assert response.status_code == 201

    assert requests.get(f"{TEST_ENDPOINT}/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["properties"]["status"] in [
        "pending",
        "parsing",
        "initializing",
        "running",
    ]


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_list_jobs(test_process_id, example_config_json):
    # this should be empty
    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    before = len(response.json()["features"])

    # make two short running jobs
    for _ in range(2):
        requests.post(
            f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
            data=json.dumps(
                dict(
                    example_config_json,
                    params=dict(example_config_json["params"], zoom=2),
                )
            ),
        )

    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    after = len(response.json()["features"])

    assert after > before


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_list_jobs_bounds(test_process_id, example_config_json):
    # this should be empty
    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=1)
            )
        ),
    )
    job_id = response.json()["id"]

    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"bounds": "0,1,2,3"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"bounds": "10,1,12,3"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_list_jobs_output_path(test_process_id, example_config_json):
    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=1)
            )
        ),
    )
    job_id = response.json()["id"]

    response = requests.get(
        f"{TEST_ENDPOINT}/jobs",
        params={"output_path": example_config_json["config"]["output"]["path"]},
    )
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"output_path": "foo"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_list_jobs_status(test_process_id, example_config_json):
    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=1)
            )
        ),
    )
    job_id = response.json()["id"]

    start = time.time()
    while True:
        time.sleep(1)
        response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}", timeout=3)
        status = response.json()["properties"]["status"]
        if status == "done":
            break
        elif time.time() - start > 120:
            raise RuntimeError(f"job not done in time, last status was '{status}'")

    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"status": "done"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"status": "cancelled"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_list_jobs_job_name(test_process_id, example_config_json):
    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=1, job_name="foo"),
            )
        ),
    )

    job_id = response.json()["id"]

    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"job_name": "foo"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"job_name": "bar"})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_list_jobs_from_date(test_process_id, example_config_json):
    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=1)
            )
        ),
    )

    job_id = response.json()["id"]

    now = date_to_str(datetime.datetime.utcfromtimestamp(time.time() - 600))
    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"from_date": now})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    future = date_to_str(datetime.datetime.utcfromtimestamp(time.time() + 600))
    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"from_date": future})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_list_jobs_to_date(test_process_id, example_config_json):
    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=1)
            )
        ),
    )

    job_id = response.json()["id"]

    time.sleep(5)
    now = date_to_str(datetime.datetime.utcfromtimestamp(time.time()))
    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"to_date": now})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id in jobs

    past = date_to_str(datetime.datetime.utcfromtimestamp(time.time() - 60))
    response = requests.get(f"{TEST_ENDPOINT}/jobs", params={"to_date": past})
    jobs = [j["id"] for j in response.json()["features"]]
    assert job_id not in jobs


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_cancel_job(test_process_id, example_config_json):
    # make one long running job
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=8)
            )
        ),
    )
    job_id = response.json()["id"]

    # make sure job is running
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.json()["properties"]["status"] in ["parsing", "running"]

    # send cancel signal
    response = requests.delete(f"{TEST_ENDPOINT}/jobs/{job_id}")

    # make sure cancel signal was received
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.json()["properties"]["status"] in ["cancelled"]

    status = response.json()["properties"]["status"]

    # see if job is cancelled
    start = time.time()
    while True:
        time.sleep(1)
        response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}", timeout=3)
        status = response.json()["properties"]["status"]
        traceback = response.json()["properties"]["traceback"] or ""
        if status == "cancelled":
            break
        elif status == "done":
            raise RuntimeError("job should not have 'done' status!")
        elif time.time() - start > 30:
            raise RuntimeError(
                f"job not cancelled in time, last status was '{status}' {traceback}"
            )
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.json()["properties"]["status"] == "cancelled"


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_cancel_jobs(test_process_id, example_config_json):
    # make one long running job
    jobs = [
        requests.post(
            f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
            data=json.dumps(
                dict(
                    example_config_json,
                    params=dict(
                        example_config_json["params"], zoom=8, bounds=[0, 1, 10, 11]
                    ),
                )
            ),
            timeout=3,
        ).json()["id"]
        for _ in range(2)
    ]

    for job_id in jobs:
        # make sure jobs are running
        response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}", timeout=3)
        assert response.json()["properties"]["status"] in ["parsing", "running"]

    # send cancel signal
    response = requests.delete(f"{TEST_ENDPOINT}/jobs/{jobs[0]}", timeout=3)

    # make sure cancel signal is stored successfully
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{jobs[0]}", timeout=3)
    assert response.json()["properties"]["status"] in ["cancelled"]

    # see if job is cancelled
    start = time.time()
    while True:
        time.sleep(1)
        response = requests.get(f"{TEST_ENDPOINT}/jobs/{jobs[0]}", timeout=3)
        status = response.json()["properties"]["status"]
        traceback = response.json()["properties"]["traceback"] or ""
        if status == "cancelled":
            break
        elif time.time() - start > 120:
            raise RuntimeError(
                f"job not cancelled in time, last status was '{status}' {traceback}"
            )

    # make sure other job has not failed
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{jobs[1]}", timeout=3)
    assert response.json()["properties"]["status"] in ["running", "done"]


@pytest.mark.skipif(
    not ENDPOINT_AVAILABLE,
    reason="requires up and running endpoint using docker-compose",
)
def test_job_result(test_process_id, example_config_json):
    result = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json, params=dict(example_config_json["params"], zoom=2)
            )
        ),
    )
    job_id = result.json()["id"]

    # see if job is cancelled
    start = time.time()
    while True:
        time.sleep(1)
        response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}", timeout=3)
        status = response.json()["properties"]["status"]
        if status == "done":
            break
        elif time.time() - start > 120:
            raise RuntimeError(f"job not finished in time, last status was '{status}'")

    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}/results")
    assert response.status_code == 200
    assert "imagesOutput" in response.json()
