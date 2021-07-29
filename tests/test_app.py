def test_get_conformance(client):
    response = client.get("/conformance")
    assert response.status_code == 200
    # TODO
    # assert response.json() == {}


def test_get_processes(client):
    response = client.get("/processes")
    assert response.status_code == 200
    # TODO
    # assert response.json() == {}


def test_post_process(client, test_process_id):
    response = client.post(f"/processes/{test_process_id}")
    assert response.status_code == 200
    # TODO
    # assert response.json() == {}


def test_post_job(client, test_process_id):
    response = client.post(f"/processes/{test_process_id}/execution")
    print(response)
    print(response.json())
    assert response.status_code == 200
    # TODO
    # assert response.json() == {}


def test_list_jobs(client):
    response = client.get("/jobs")
    assert response.status_code == 200
    # TODO
    # assert response.json() == {}


def test_get_job(client, redis):
    # TODO get job id
    response = client.get(f"/jobs/{test_job_id}")
    assert response.status_code == 200
    # TODO
    # assert response.json() == {}


def test_cancel_job(client, redis):
    # TODO get job id
    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200
    # TODO
    # assert response.json() == {}


def get_job_result(client):
    # TODO get job id
    response = client.get(f"/jobs/{test_job_id}/result")
    assert response.status_code == 200
    # TODO
    # assert response.json() == {}
