import json


# def test_get_conformance(client):
#     response = client.get("/conformance")
#     assert response.status_code == 200
#     # TODO
#     # assert response.json() == {}


def test_get_processes(client):
    response = client.get("/processes")
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_get_process(client):
    response = client.get("/processes/mapchete.processes.convert")
    assert response.status_code == 200
    assert "title" in response.json()


# def test_post_process(client, test_process_id):
#     response = client.post(f"/processes/{test_process_id}")
#     assert response.status_code == 200
#     # TODO
#     # assert response.json() == {}


def test_post_job(client, test_process_id, example_config_json):
    # response = client.get("/jobs")
    response = client.post(
        f"/processes/{test_process_id}/execution",
        data=json.dumps(example_config_json)
    )
    assert response.status_code == 201

    assert client.get("/jobs/").json()

    # check if job is submitted
    job_id = response.json()["id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200


def test_list_jobs(client, test_process_id, example_config_json):
    # this should be empty
    response = client.get("/jobs")
    assert response.status_code == 200
    before = len(response.json())

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
    after = len(response.json())

    assert after > before


# def test_cancel_job(client, test_process_id, example_config_json):
#     # make one long running job
#     response = client.post(
#         f"/processes/{test_process_id}/execution",
#         data=json.dumps(
#             dict(
#                 example_config_json,
#                 params=dict(example_config_json["params"], zoom=12)
#             )
#         )
#     )
#     job_id = response.json()["id"]

#     # make sure job is running
#     response = client.get(f"/jobs/{job_id}")
#     assert response.json()["properties"]["state"] == "running"

#     # send cancel signal
#     response = client.delete(f"/jobs/{job_id}")

#     response = client.get(f"/jobs/{job_id}")
#     assert response.json()["properties"]["state"] == "aborting"


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
