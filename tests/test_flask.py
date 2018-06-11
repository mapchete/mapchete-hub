# def test_start(client, baseurl):
#     task_id = "test"
#     url = "%s/jobs/%s" % (baseurl, task_id)
#     response = client.get(url)
#     assert response.status_code == 200
#     assert response.json["task_id"] == task_id
#     assert response.json["status"] == "sent"


def test_status(client, baseurl):
    task_id = "jobs"
    url = "%s/status/%s" % (baseurl, task_id)
    response = client.get(url)
    assert response.status_code == 200
    assert response.json["task_id"] == task_id
    assert response.json["status"] == "PENDING"
