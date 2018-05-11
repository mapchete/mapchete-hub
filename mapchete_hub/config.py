def get_host_options():
    return dict(
        host_ip='0.0.0.0',
        port=5000
    )


def get_flask_options():
    return dict(
        broker_url='amqp://guest:guest@localhost:5672//',
        result_backend='rpc://guest:guest@localhost:5672//',
    )


def get_celery_options():
    return dict(
        broker_url='amqp://guest:guest@localhost:5672//',
        result_backend='rpc://guest:guest@localhost:5672//',
    )
