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
    "aioredis>=2.0.0a1",
    "cached_property",
    "dask",
    "dask-gateway",
    "distributed",
    "fastapi==0.66",
    "mapchete[contours,geobuf,http,s3,vrt]>=2022.9.0",
    "mongomock",
    "odmantic",
    "pymongo",
    "uvicorn",
]
slack_requires = ["Slacker"]
test_requires = [
    "pytest",
    "pytest-cov",
    "pytest-env",
    "pytest-mongodb",
    "requests",
]
xarray_requires = ["mapchete_xarray>=2022.5.0"]
complete_requires = install_requires + slack_requires + xarray_requires

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
        "console_scripts": ["mhub-server=mapchete_hub.cli:main"],
    },
    install_requires=install_requires,
    extras_require={
        "complete": complete_requires,
        "slack": slack_requires,
        "test": test_requires,
        "xarray": xarray_requires,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-flask"],
)
