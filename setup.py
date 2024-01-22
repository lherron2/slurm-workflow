from setuptools import setup, find_packages
import os

setup(
    name="slurm-flow",
    version="0.1",
    packages=find_packages(),
    install_requires=[],
    tests_require=[
        'unittest'
    ],
    author="Lukas",
    author_email="lherron@umd.edu",
    description="A Python module to study molecular dynamics simulations using Thermodynamic Maps",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

