import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cadence-client",
    version="1.0.0-beta3",
    author="Mohammed Firdaus",
    author_email="firdaus.halim@gmail.com",
    description="Python framework for Cadence Workflow Service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/firdaus/cadence-python",
    packages=setuptools.find_packages(exclude=["cadence.tests", "cadence.spikes"]),
    install_requires=[
        "dataclasses-json>=0.3.8",
        "more-itertools>=7.0.0",
        "ply>=3.11",
        "tblib>=1.6.0",
        "thriftrw>=1.7.2",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True
)
