#!/usr/bin/env python3

from bson.objectid import ObjectId
import click
import requests
from requests.exceptions import ConnectionError
import time

MAX_RETRIES = 3
RETRY_WAIT = 5


@click.command()
@click.option('--baseurl', default="http://localhost:5000")
def run_test(baseurl):
    """Simple program that greets NAME for a total of COUNT times."""
    retries = 0
    while True:
        try:
            # (1) execute one job
            #####################
            job_id = str(ObjectId())

            # no job with this ID should exist
            print("assert we get a 404")
            response = requests.get("{}/jobs/{}".format(baseurl, job_id))
            print(response.json())
            assert response.status_code == 404
            print("OK")

            # let's create a new job
            print("post a new job")
            response = requests.post(
                "{}/jobs/{}".format(baseurl, job_id), json={"id": job_id}
            )
            print(response.json())
            assert response.status_code == 202
            print("OK")

            # voilá, a new job with this ID is there
            print("assert we get a 200")
            response = requests.get("{}/jobs/{}".format(baseurl, job_id))
            print(response.json())
            assert response.status_code == 200
            assert response.json()["id"] == job_id
            print("OK")

            # let's get the job state until it is finished
            # don't do it more than 10 times
            max_requests = 30
            request_count = 0
            while True:
                request_count += 1
                if request_count > max_requests:
                    raise RuntimeError("mhub did not process job")
                print("get job state")
                response = requests.get("{}/jobs/{}".format(baseurl, job_id))
                print(response.json())
                assert response.status_code == 200
                if response.json().get("state") == "SUCCESS":
                    break
                elif response.json().get("state") == "FAILURE":
                    raise ValueError("job failed")
                time.sleep(1)
            print("OK")

            # (2) execute and cancel jobs
            #############################
            first_job_id = str(ObjectId())
            second_job_id = str(ObjectId())

            # let's create two new jobs
            for job_id in [first_job_id, second_job_id]:
                print("post a new job")
                response = requests.post(
                    "{}/jobs/{}".format(baseurl, job_id), json={"id": job_id}
                )
                print(response.json())
                assert response.status_code == 202
                print("OK")

                # voilá, a new job with this ID is there
                print("assert we get a 200")
                response = requests.get("{}/jobs/{}".format(baseurl, job_id))
                print(response.json())
                assert response.status_code == 200
                assert response.json()["id"] == job_id
                print("OK")

            # wait a couple of seconds
            print("Wait for a couple of seconds ...")
            time.sleep(1)

            # cancel jobs by posting via PUT
            for job_id in [first_job_id, second_job_id]:
                print("cancel job")
                response = requests.put(
                    "{}/jobs/{}".format(baseurl, job_id), json={"command": "cancel"}
                )
                print(response.json())
                assert response.status_code == 200
                print("OK")

            # wait a couple of seconds
            print("Wait for a couple of seconds ...")
            time.sleep(3)

            # make sure first job state is TERMINATED
            print("assert we get a 200")
            response = requests.get("{}/jobs/{}".format(baseurl, first_job_id))
            print(response.json())
            assert response.status_code == 200
            assert response.json()["state"] == "TERMINATED"
            print("OK")

            # make sure second job state is TERMINATED
            print("assert we get a 200")
            response = requests.get("{}/jobs/{}".format(baseurl, second_job_id))
            print(response.json())
            assert response.status_code == 200
            assert response.json()["state"] == "TERMINATED"
            print("OK")

            break
        except ConnectionError as e:
            retries += 1
            if retries == MAX_RETRIES:
                print("no retries left")
                raise e
            print("no connection to {}, waiting for retry ...".format(baseurl))
            time.sleep(RETRY_WAIT)


if __name__ == '__main__':
    run_test()