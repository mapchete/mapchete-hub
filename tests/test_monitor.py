from shapely.geometry import shape

from mapchete_hub.monitor import StatusHandler


def test_statushandler(status_gpkg, status_profile):
    test_job = "test_job"
    another_test_job = "another_test_job"

    pending = {
        'args': '()',
        'type': 'task-sent',
        'clock': 90,
        'timestamp': 1528190160.3892283,
        'kwargs': '{"command": "execute", "queue": "execute_queue", "parent_job_id": "", "child_job_id": "", "process_area": "POLYGON ((4 1, 4 2, 3 2, 3 1, 4 1))", "mode": "continue", "bounds": null, "tile": null, "point": null, "mapchete_config": {"process_bounds": [3.0, 1.0, 4.0, 2.0], "some_integer_parameter": 12, "some_bool_parameter": true, "some_float_parameter": 5.3, "output": {"dtype": "float32", "bands": 1, "path": "test", "format": "GTiff"}, "process_file": "example_process.py", "some_string_parameter": {"zoom<=7": "string1", "zoom>7": "string2"}, "zoom_levels": {"min": 7, "max": 11}, "pyramid": {"grid": "geodetic", "metatiling": 4}, "input": {"file1": {"zoom>=10": "dummy1.tif"}, "file2": "dummy2.tif"}}, "wkt_geometry": null, "zoom": null}',
        'root_id': 'hanse',
        'hostname': 'gen6329@tycho2',
        'local_received': 1528190160.3903759,
        'uuid': test_job,
        'routing_key': 'zone_queue',
        'eta': None,
        'name': 'mapchete_hub.workers.zone_worker.run',
        'exchange': '',
        'expires': None,
        'retries': 0,
        'utcoffset': -2,
        'state': 'PENDING',
        'queue': 'zone_queue',
        'parent_id': None,
        'pid': 6329
    }

    progress = {
        'utcoffset': -2,
        'timestamp': 1528185898.6538837,
        'clock': 3,
        'type': 'task-progress',
        'pid': 31546,
        'hostname': 'zone_worker@tycho2',
        'progress_data': {'current': 3, 'total': 24},
        'state': 'PROGRESS',
        'uuid': test_job,
        'local_received': 1528185898.7191732
    }

    success = {
        'clock': 64,
        'pid': 20106,
        'uuid': test_job,
        'runtime': 40.91311929101357,
        'state': 'SUCCESS',
        'timestamp': 1527938183.97571,
        'hostname': 'zone_worker@tycho2',
        'utcoffset': -2,
        'local_received': 1527938183.9801202,
        'result': 'None',
        'type': 'task-succeeded'
    }

    failure = {
        'utcoffset': -2,
        'pid': 16322,
        'local_received': 1527934867.8697965,
        'traceback': 'Traceback (most recent call last):  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/celery/app/trace.py", line 382, in trace_task\n    R = retval = fun(*args, **kwargs)\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/celery/app/trace.py", line 641, in __protected_call__\n    return self.run(*args, **kwargs)\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/workers/zone_worker.py", line 24, in run\n    for i, _ in enumerate(executor):\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/_core.py", line 39, in mapchete_execute\n    chunksize=min([max([total_tiles // multi, 1]), max_chunksize])\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/billiard-3.5.0.3-py3.5.egg/billiard/pool.py", line 1920, in next\n    raise Exception(value)\nException: Traceback (most recent call last):\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\n    process_data = self.config.process_func(tile_process)\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\n    assert randint(0, 500)\nAssertionError\n\nDuring handling of the above exception, another exception occurred:\n\nTraceback (most recent call last):\n  File "/home/ungarj/virtualenvs/p3/lib/python3.5/site-packages/billiard-3.5.0.3-py3.5.egg/billiard/pool.py", line 358, in workloop\n    result = (True, prepare_result(fun(*args, **kwargs)))\n  File "/home/ungarj/git/mapchete_hub/mapchete_hub/_core.py", line 79, in _process_worker\n    output = process.execute(process_tile, raise_nodata=True)\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 268, in execute\n    return self._execute(process_tile, raise_nodata=raise_nodata)\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 507, in _execute\n    raise MapcheteProcessException(format_exc())\nmapchete.errors.MapcheteProcessException: Traceback (most recent call last):\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\n    process_data = self.config.process_func(tile_process)\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\n    assert randint(0, 500)\nAssertionError\n\n\n', 'exception': 'Exception(<ExceptionInfo: MapcheteProcessException(\'Traceback (most recent call last):\\n  File "/home/ungarj/git/mapchete/mapchete/_core.py", line 491, in _execute\\n    process_data = self.config.process_func(tile_process)\\n  File "/home/ungarj/git/mapchete_hub/tests/testdata/example_process.py", line 8, in execute\\n    assert randint(0, 500)\\nAssertionError\\n\',)>,)',
        'uuid': test_job,
        'type': 'task-failed',
        'hostname': 'zone_worker@tycho2',
        'timestamp': 1527934867.8687088,
        'clock': 10,
        'state': 'FAILURE'
    }

    another_pending = dict(pending, uuid=another_test_job)

    with StatusHandler(status_gpkg, mode='w', profile=status_profile) as status_w:
        with StatusHandler(status_gpkg, mode='r') as status_r:
            # write pending event
            status_w.update(test_job, pending)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty
            for k in pending.keys():
                if k in status_profile['schema']:
                    assert pending[k] == current['properties'][k]

            # write progress event
            status_w.update(test_job, progress)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty
            for k in progress.keys():
                if k in status_profile['schema']:
                    assert progress[k] == current['properties'][k]

            # write success event
            status_w.update(test_job, success)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty
            for k in success.keys():
                if k in status_profile['schema']:
                    assert success[k] == current['properties'][k]

            # write fail event
            status_w.update(test_job, failure)
            current = status_r.job(test_job)
            geom = shape(current['geometry'])
            assert geom.is_valid
            assert not geom.is_empty
            for k in failure.keys():
                if k in status_profile['schema']:
                    assert failure[k] == current['properties'][k]

            # write another job
            status_w.update(another_test_job, another_pending)
            all_jobs = status_r.all()
            assert len(all_jobs) == 2

            # filter by state
            assert len(status_r.all(state="SUCCESS")) == 0
            assert len(status_r.all(state="FAILURE")) == 1
            assert len(status_r.all(state="done")) == 1
            assert len(status_r.all(state="PENDING")) == 1
            assert len(status_r.all(state="todo")) == 1

            # filter by output path
            assert len(status_r.all(output_path="test")) == 2

            # filter by command
            assert len(status_r.all(command="execute")) == 2

            # filter by queue
            assert len(status_r.all(queue="execute_queue")) == 0

            # filter by bounds
            assert len(status_r.all(bounds=[1, 2, 3, 4])) == 2
            assert len(status_r.all(bounds=[11, 12, 13, 14])) == 0
