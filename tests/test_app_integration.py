import json
import os
import pytest
import requests
import time


TEST_ENDPOINT = os.environ.get("MHUB_HOST", "http://0.0.0.0:5000")

def _endpoint_available():
    try:
        response = requests.get(TEST_ENDPOINT)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


ENDPOINT_AVAILABLE = _endpoint_available()


@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
def test_get_root():
    response = requests.get(f"{TEST_ENDPOINT}/")
    assert response.status_code == 200
    assert response.json()


# @pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
# def test_get_conformance():
#     # TODO
#     with pytest.raises(NotImplementedError):
#         response = requests.get(f"{TEST_ENDPOINT}/conformance")


@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
def test_get_processes():
    response = requests.get(f"{TEST_ENDPOINT}/processes")
    assert response.status_code == 200
    assert len(response.json()) > 0


@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
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


@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
def test_post_job(test_process_id, example_config_json):
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(example_config_json)
    )
    assert response.status_code == 201

    assert requests.get(f"{TEST_ENDPOINT}/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.status_code == 200


@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
def test_post_job_custom_process(test_process_id, example_config_custom_process_json):
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(example_config_custom_process_json)
    )
    assert response.status_code == 201

    assert requests.get(f"{TEST_ENDPOINT}/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["properties"]["state"] == "running"


@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
def test_list_jobs(test_process_id, example_config_json):
    # this should be empty
    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    before = len(response.json())

    # make two short running jobs

    for _ in range(2):
        requests.post(
            f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
            data=json.dumps(
                dict(
                    example_config_json,
                    params=dict(example_config_json["params"], zoom=2)
                )
            )
        )

    response = requests.get(f"{TEST_ENDPOINT}/jobs")
    assert response.status_code == 200
    after = len(response.json())

    assert after > before


@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
def test_cancel_job(test_process_id, example_config_json):
    # make one long running job
    response = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=12)
            )
        )
    )
    job_id = response.json()["id"]

    # make sure job is running
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.json()["properties"]["state"] == "running"

    # send cancel signal
    response = requests.delete(f"{TEST_ENDPOINT}/jobs/{job_id}")

    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.json()["properties"]["state"] == "aborting"

    # see if job is cancelled
    time.sleep(10)
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}")
    assert response.json()["properties"]["state"] == "cancelled"


@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
def test_cancel_jobs(test_process_id, example_config_json):
    # make one long running job
    jobs = [
        requests.post(
            f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
            data=json.dumps(
                dict(
                    example_config_json,
                    params=dict(example_config_json["params"], zoom=12)
                )
            ),
            timeout=3
        ).json()["id"]
        for _ in range(2)
    ]

    for job_id in jobs:
        # make sure jobs are running
        response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}", timeout=3)
        assert response.json()["properties"]["state"] == "running"

    # send cancel signal
    response = requests.delete(f"{TEST_ENDPOINT}/jobs/{jobs[0]}", timeout=3)

    # make sure cancel signal is stored successfully
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{jobs[0]}", timeout=3)
    assert response.json()["properties"]["state"] in ["aborting", "cancelled"]

    # see if job is cancelled
    start = time.time()
    while True:
        time.sleep(1)
        response = requests.get(f"{TEST_ENDPOINT}/jobs/{jobs[0]}", timeout=3)
        state = response.json()["properties"]["state"]
        traceback = response.json()["properties"]["traceback"] or ""
        if state == "cancelled":
            break
        elif time.time() - start > 120:
            raise RuntimeError(f"job not cancelled in time, last state was '{state}' {traceback}")

    # make sure other job has not failed
    response = requests.get(f"{TEST_ENDPOINT}/jobs/{jobs[1]}", timeout=3)
    assert response.json()["properties"]["state"] in ["running", "done"]



@pytest.mark.skipif(not ENDPOINT_AVAILABLE, reason="requires up and running endpoint using docker-compose")
def test_job_result(test_process_id, example_config_json):
    result = requests.post(
        f"{TEST_ENDPOINT}/processes/{test_process_id}/execution",
        data=json.dumps(
            dict(
                example_config_json,
                params=dict(example_config_json["params"], zoom=2)
            )
        )
    )
    job_id = result.json()["id"]

    response = requests.get(f"{TEST_ENDPOINT}/jobs/{job_id}/result")
    assert response.status_code == 200
    assert "tmp" in response.json()
