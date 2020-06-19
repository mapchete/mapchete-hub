#!/usr/bin/env python3

import click
import os
from requests.exceptions import ConnectionError
import time
import uuid

from mapchete_hub.api import API
from mapchete_hub.exceptions import JobNotFound

MAX_RETRIES = 3
RETRY_WAIT = 5


@click.command()
@click.option('--baseurl', default="http://localhost:5000")
def run_test(baseurl):
    """Simple program that greets NAME for a total of COUNT times."""
    retries = 0
    while True:
        try:
            api = API(baseurl, timeout=15)

            # (1) execute one job
            #####################
            job_id = uuid.uuid4().hex

            # no job with this ID should exist
            print("assert job is not found")
            try:
                api.job(job_id)
            except JobNotFound:
                print("OK")

            # let's create a new job
            print("post a new job")
            response = api.start_job(
                mapchete_config=os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "testdata/test.mapchete"
                ),
                command="execute",
                job_id=job_id,
                bounds=[-1, 0, 0, 1]
            )
            print(response.json)
            assert response.status_code == 202
            print("OK")

            # voilá, a new job with this ID is there
            print("assert we get a 200")
            response = api.job(job_id)
            assert response.status_code == 200
            assert response.json["id"] == job_id
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
                response = api.job(job_id)
                print(response.json)
                assert response.status_code == 200
                if response.json["properties"].get("state") == "SUCCESS":
                    break
                elif response.json["properties"].get("state") == "FAILURE":
                    raise ValueError("job failed")
                time.sleep(2)
            print("OK")

            # (2) execute and cancel jobs
            #############################
            first_job_id = uuid.uuid4().hex
            second_job_id = uuid.uuid4().hex

            # let's create two new jobs
            for job_id in [first_job_id, second_job_id]:
                print("post a new job")
                response = api.start_job(
                    mapchete_config=os.path.join(
                        os.path.dirname(os.path.realpath(__file__)),
                        "testdata/test.mapchete"
                    ),
                    command="execute",
                    job_id=job_id,
                    bounds=[-1, 0, 0, 1]
                )
                assert response.status_code == 202
                print("OK")

                # voilá, a new job with this ID is there
                print("assert we get a 200")
                response = api.job(job_id)
                print(response.json)
                assert response.status_code == 200
                assert response.json["id"] == job_id
                print("OK")

            # wait a couple of seconds
            print("Wait for a couple of seconds ...")
            time.sleep(1)

            # cancel jobs by posting via PUT
            for job_id in [first_job_id, second_job_id]:
                print("cancel job")
                response = api.cancel_job(job_id)
                print(response.json)
                assert response.status_code == 200
                print("OK")

            # wait a couple of seconds
            print("Wait for a couple of seconds ...")
            # we need to wait that long because sometimes shutting down billiard
            # workers takes a while
            time.sleep(60)

            for job_id in [first_job_id, second_job_id]:
                # make sure first job state is TERMINATED
                print("assert we get a 200")
                response = api.job(job_id)
                print(response.json)
                assert response.status_code == 200
                assert response.json["id"] == job_id
                assert response.json["properties"]["state"] == "TERMINATED"
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
