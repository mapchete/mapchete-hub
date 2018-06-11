import os


def get_host_options():
    default = dict(
        host_ip='0.0.0.0',
        port=5000
    )
    return _get_opts(default)


def get_flask_options():
    default = dict(
        broker_url='amqp://guest:guest@localhost:5672//',
        result_backend='rpc://guest:guest@localhost:5672//',
        # required to hanlde exceptions raised by billiard
        result_serializer='pickle',
        task_serializer='pickle',
        event_serializer='pickle',
        accept_content=['pickle', 'json'],
        task_routes={'mapchete_hub.workers.zone_worker.*': {'queue': 'zone_queue'}},
        task_acks_late=True,
        worker_send_task_events=True,
        task_send_sent_event=True,
        event_queue_expires=604800  # one week in seconds
    )
    opts = _get_opts(default)
    print(opts)
    return opts


def get_main_options():
    default = dict(
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
        config_dir="/home/ungarj/git/mapchete_hub/tests/testdata/"
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
