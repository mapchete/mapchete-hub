from billiard import Pool
from functools import partial
import time

from mapchete_hub.celery_app import celery_app


def _worker(i):
    time.sleep(1)
    return "done!"


@celery_app.task(track_started=True)
def run():
    # use multiprocessing via celery-friendly package billiard
    f = partial(_worker)
    pool = Pool()
    for result in pool.imap_unordered(f, range(100)):
        print(result)
    return "yay"
