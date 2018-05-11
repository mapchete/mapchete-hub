import concurrent.futures

from mapchete_hub.celery_app import celery_app


@celery_app.task(track_started=True)
def run():
    import time

    # 10 seconds single task
    print("start task")
    1/0
    time.sleep(10)
    return "yay"

    # # multiprocessing example
    # def _worker(i):
    #     time.sleep(1)

    # with concurrent.futures.ProcessPoolExecutor() as executor:
    #     tasks = (
    #         executor.submit(_worker, i)
    #         for i in range(100)
    #     )
    #     for task in concurrent.futures.as_completed(tasks):
    #         print(task)
