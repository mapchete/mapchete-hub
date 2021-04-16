"""Install Mapchete."""

from setuptools import setup, find_packages

# get version number
# from https://github.com/mapbox/rasterio/blob/master/setup.py#L55
with open("mapchete_hub/__init__.py") as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue


install_requires = [
    "celery<5.0.0",
    "celery-slack",
    "click",
    "click-spinner",
    "environ-config",
    "Flask-Celery-py3",
    "flask_pymongo",
    "flask_restful",
    "fsspec==0.8.7",
    "future",
    "geojson",
    "mapchete>=0.31",
    "mongomock",
    "pymongo",
    "requests",
    "slacker",
    "tornado>=4.2.0,<6.0.0",
    "webargs>=6.0.0,<7.0.0",
    "xarray",
]
mundi_requires = [
    "xmltodict"
]
test_requires = [
    "pytest",
    "pytest-cov",
    "pytest-env",
    "pytest-flask",
    "pytest-mongodb",
]

setup(
    name="mapchete_hub",
    version=version,
    description="distributed mapchete processing",
    author="Joachim Ungar",
    author_email="joachim.ungar@eox.at",
    url="https://gitlab.eox.at/maps/mapchete_hub",
    license="MIT",
    packages=find_packages(),
    entry_points={
        "console_scripts": ["mhub=mapchete_hub.cli:mhub"],
        "mapchete.cli.commands": ["mhub=mapchete_hub.cli:mhub"],
    },
    install_requires=install_requires,
    extras_require={
        "complete": install_requires + mundi_requires,
        "mundi": mundi_requires,
        "test": test_requires
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-flask"]
)
