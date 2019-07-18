"""Install Mapchete."""

import os
from setuptools import setup, find_packages

# get version number
# from https://github.com/mapbox/rasterio/blob/master/setup.py#L55
with open('mapchete_hub/__init__.py') as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            continue


def parse_requirements(file):
    return sorted(set(
        line.partition('#')[0].strip()
        for line in open(os.path.join(os.path.dirname(__file__), file))
    ) - set(''))


setup(
    name='mapchete_hub',
    version=version,
    description='distributed mapchete processing',
    author='Joachim Ungar',
    author_email='joachim.ungar@eox.at',
    url='https://gitlab.eox.at/maps/mapchete_hub',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'console_scripts': ['mhub=mapchete_hub.cli:mhub'],
        'mapchete.cli.commands': ["mhub=mapchete_hub.cli:mhub"],
    },
    install_requires=parse_requirements('requirements.txt'),
    extras_require={
        'mundi': parse_requirements('requirements_mundi.txt'),
        's1': parse_requirements('requirements_s1.txt'),
        'test': parse_requirements('requirements_test.txt')
    },
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
