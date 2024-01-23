# Slurm Workflow

## Description
The `slurmflow` package contains three classes for implementing efficient workflows. The `config.py` script contains the `ConfigParser` which extends the YAML file format to support a string-substitution syntax (see `config.ipynb` for more). `driver.py` contains the `SlurmDriver` which is a thin wrapper around SLURM that enables workflows to be scripted in python rather than bash (see `driver.ipynb`). The `serializer.py` script contains the `ObjectSerializer`, which compresses and stores (nearly) arbitrary python objects (see `serializer.ipynb`).

## Installation via pip
`pip install slurm-workflow`

## Installation from source
1. Clone the repository: `git clone https://github.com/lherron2/slurm-workflow.git`.
2. Navigate to the cloned directory: `cd slurm-workflow`.
3. Install the required dependencies: `python setup.py install`.

## Structure
- `config/`: Contains configuration files for customizing workflows.
- `config.ipynb`: Jupyter Notebook showcasing the `ConfigParser`.
- `driver.ipynb`: Jupyter Notebook showcasing the `SlurmDriver`.
- `serializer.ipynb`: Jupyter Notebook showcasing the `ObjectSerializer`.
- `slurmflow/`: Core modules and scripts for the Slurm Workflow.
  
## License
This project is under the [MIT License](LICENSE).



