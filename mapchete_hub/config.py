def get_host_options():
    return dict(
        host_ip='0.0.0.0',
        port=5000
    )


def get_flask_options():
    return dict(
        broker_url='amqp://guest:guest@localhost:5672//',
        result_backend='rpc://guest:guest@localhost:5672//',
        # required to hanlde exceptions raised by billiard
        result_serializer='pickle',
        accept_content=['pickle', 'json'],
        task_routes={'mapchete_hub.workers.zone_worker.*': {'queue': 'zone_queue'}},
        task_acks_late=True,
    )


# def get_celery_options():
#     return dict(
#         broker_url='amqp://guest:guest@localhost:5672//',
#         result_backend='rpc://guest:guest@localhost:5672//',
#         CELERY_TASK_SERIALIZER='pickle',
#         CELERY_EVENT_SERIALIZER='pickle',
#         CELERY_RESULT_SERIALIZER='pickle',
#     )
