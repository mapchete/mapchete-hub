import datetime
import json
import logging

from mapchete_hub.workers import zone_worker, preview_worker
from mapchete_hub._core import cleanup_config

logger = logging.getLogger(__name__)


workers = {
    'zone_worker': zone_worker,
    'preview_worker': preview_worker
}


def send_to_queue(
    job_id=None,
    worker=None,
    config=None,
    process_area=None
):
    if worker not in workers.keys():
        raise ValueError('unknown worker: %s')
    kwargs = dict(
        config=cleanup_config(cleanup_datetime(config)),
        process_area=process_area.wkt
    )
    logger.debug(config)
    logger.debug("send to %s queue", worker)
    logger.debug(kwargs)
    workers[worker].run.apply_async(
        args=(None, ),
        kwargs=kwargs,
        task_id=job_id,
        kwargsrepr=json.dumps(kwargs),
        link=get_next_jobs(
            job_id=job_id,
            config=config,
            process_area=process_area.wkt
        )
    )


def get_next_jobs(job_id=None, config=None, process_area=None):
    logger.debug(config.keys())

    def _gen_next_job(next_c):
        logger.debug(next_c.keys())
        while True:
            if 'mhub_next_process' in next_c:
                job_conf = next_c['mhub_next_process']
                worker = job_conf['mhub_worker']
                kwargs = dict(
                    config=cleanup_config(dict(mapchete_config=next_c)),
                    process_area=process_area
                )
                task_id = '%s_%s' % (worker, job_id)
                kwargsrepr = json.dumps(kwargs)
                yield workers[worker].run.signature(
                    args=(None, ),
                    kwargs=kwargs,
                    task_id=task_id,
                    kwargsrepr=kwargsrepr
                )
                next_c = job_conf
            else:
                break

    mp_config = cleanup_datetime(config['mapchete_config'])
    return list(_gen_next_job(mp_config))


def cleanup_datetime(d):
    """Represent timestamps as strings, not datetime.date objects."""
    return {
        k: cleanup_datetime(v) if isinstance(v, dict)
        else str(v) if isinstance(v, datetime.date) else v
        for k, v in d.items()
    }
