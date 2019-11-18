from mapchete_hub.config import cleanup_datetime


def test_get_all_jobs(client):
    url = "/jobs/"
    response = client.get(url)
    assert response.status_code == 200
    assert len(response.json) == 0


def test_get_one_job(client):
    job_id = "test"
    url = "/jobs/%s" % job_id
    response = client.get(url)
    assert response.status_code == 404


def test_start_job(client, example_mapchete):
    job_id = "test"
    url = "/jobs/%s" % job_id
    config = dict(example_mapchete.dict)
    # config.pop("mhub_next_process")

    data = cleanup_datetime(
        dict(
            mapchete_config=config,
            zoom=11,
            point=None,
            wkt_geometry=None,
            tile=(11, 244, 517),
            mode="continue"
        )
    )
    response = client.post(url, json=data)
    assert response.status_code == 202
    assert "geometry" in response.json
    assert "properties" in response.json
    assert response.json["properties"]["state"] == "PENDING"

    # TODO this doesn't work in test mode because there is no monitor available
    # submit again and get error
    # response = client.post(url, json=data)
    # assert response.status_code == 406
    # assert "geometry" in response.json
    # assert "properties" in response.json
    # assert response.json["properties"]["state"] == "EXISTS"
