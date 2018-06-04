"""Install Mapchete."""

from setuptools import setup

# get version number
# from https://github.com/mapbox/rasterio/blob/master/setup.py#L55
with open('mapchete_hub/__init__.py') as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue

setup(
    name='mapchete_hub',
    version=version,
    description='distributed mapchete processing',
    author='Joachim Ungar',
    author_email='joachim.ungar@eox.at',
    url='https://gitlab.eox.at/maps/orgonite',
    license='MIT',
    packages=[
        'mapchete_hub.cli',
    ],
    entry_points={
        'console_scripts': [
            'mhub=mapchete_hub.cli:mhub'
        ]
    },
    install_requires=[
        'celery',
        'celery-flower',
        'click',
        'Flask-Celery-py3',
        'mapchete>=0.21',
        'pysqlite3'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: GIS',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-flask']
)
