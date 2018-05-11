from flask import Flask, jsonify

from mapchete_hub.celery_app import celery_app
from mapchete_hub.config import get_flask_options
from mapchete_hub.workers import zone_worker


def flask_app(config=None, no_sql=False):
    """Flask application factory. Initializes and returns the Flask application."""
    app = Flask(__name__)
    conf = get_flask_options()
    if config:
        conf.update(**config)
    app.config.update(conf)

    celery_app.conf.update(app.config)
    celery_app.init_app(app)

    @app.route('/status/<task_id>')
    def status(task_id):
        res = celery_app.AsyncResult(task_id)
        res_meta = res.backend.get_task_meta(task_id),
        if res.status == "FAILURE":
            print("HOHOHO")
            print(res_meta)
            print("Ahsah")
        return jsonify(dict(
            res_meta,
            task_id=task_id
        ))

    @app.route('/start/<task_id>')
    def start(task_id):
        res = zone_worker.run.apply_async(task_id=task_id)
        return "sent task named " + res.id

    # Return the application instance.
    return app
