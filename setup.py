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
    "distributed",
    "fastapi==0.66",
    "mapchete[contours,geobuf,http,s3,vrt]>=0.40",
    "mongomock",
    "odmantic",
    "pymongo",
    "uvicorn",
]
test_requires = [
    "pytest",
    "pytest-cov",
    "pytest-env",
    "pytest-mongodb",
    "requests",
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
    install_requires=install_requires,
    extras_require={
        "complete": install_requires,
        "test": test_requires
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "pytest-flask"]
)
