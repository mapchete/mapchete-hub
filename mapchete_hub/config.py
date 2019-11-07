import os


def _get_host_options():
    default = dict(host_ip='0.0.0.0', port=5000)
    return _get_opts(default)


def _get_flask_options():
    default = dict(
        broker_url='amqp://guest:guest@localhost:5672//',
        result_backend='rpc://guest:guest@localhost:5672//',
        # required to hanlde exceptions raised by billiard
        result_serializer='pickle',
        task_serializer='pickle',
        event_serializer='pickle',
        accept_content=['pickle', 'json'],
        task_routes={
            'mapchete_hub.workers.execute.*': {'queue': 'execute_queue'},
            'mapchete_hub.workers.index.*': {'queue': 'index_queue'},
        },
        task_acks_late=True,
        worker_send_task_events=True,
        worker_hijack_root_logger=False,
        task_send_sent_event=True,
        event_queue_expires=604800,  # one week in seconds
    )
    opts = {}
    for k, v in _get_opts(default).items():
        opts[k] = v
        opts["CELERY_" + k.upper()] = v
    return opts


def _get_main_options():
    default = dict(
        config_dir="/tmp/",
        status_gpkg='status.gpkg',
        status_gpkg_profile=dict(
            crs={'init': 'epsg:4326'},
            driver="GPKG",
            schema=dict(
                geometry='Polygon',
                properties=dict(
                    job_id='str:100',
                    config='str:1000',
                    state='str:50',
                    timestamp='float',
                    started='float',
                    hostname='str:50',
                    progress_data='str:100',
                    runtime='float',
                    exception='str:100',
                    traceback='str:1000',
                )
            )
        ),
    )
    return _get_opts(default)


def _get_opts(default):
    """
    Use environmental variables starting with 'MHUB_', otherwise fall back to default
    values.
    """
    return {
        k: os.environ.get('MHUB_' + k.upper(), default.get(k)) for k in default.keys()
    }


host_options = _get_host_options()
flask_options = _get_flask_options()
main_options = _get_main_options()
timeout = 5
