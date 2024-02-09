from setuptools import setup, find_packages
import os

setup(
    name="slurm-workflow",
    version="0.17",
    packages=find_packages(),
    install_requires=[
        'numpy',
        'h5py',
        'blosc2',
        'dill',
        'pyyaml',
        ],
    author="Lukas",
    author_email="lherron@umd.edu",
    description="A Python module for running workflows on a Slurm cluster.",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

