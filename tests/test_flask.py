import uuid


def test_get_capabilities(client):
    url = "/capabilities.json"
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.json)


def test_get_jobs(client):
    response = client.get("jobs")
    assert response.status_code == 200


def test_create_job(client, new_job_metadata):
    job_id = uuid.uuid4().hex
    job_data = {
        k: v for k, v in new_job_metadata.items()
        if k in ["config", "params", "command"]
    }

    # assert we get a 404
    response = client.get("jobs/{}".format(job_id))
    assert response.status_code == 404

    # post a new job
    response = client.post("jobs/{}".format(job_id), json=job_data)
    assert response.status_code == 202

    # assert we get a 200
    response = client.get("jobs/{}".format(job_id))
    assert response.status_code == 200
    assert response.json["id"] == job_id

    # TODO this doesn't work in test mode because there is no monitor available
    # submit again and get error
    response = client.post("jobs/{}".format(job_id), json=job_data)
    assert response.status_code == 409
    assert "job already exists" in response.json["message"]
