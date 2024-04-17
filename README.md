# Slurm Workflow

## Description
The `slurmflow` package contains three classes for implementing efficient workflows. The `config.py` script contains the `ConfigParser` which extends the YAML file format to support a string-substitution syntax (see `config.ipynb` for more). `driver.py` contains the `SlurmDriver` which is a thin wrapper around SLURM that enables workflows to be scripted in python rather than bash (see `driver.ipynb`). The `serializer.py` script contains the `ObjectSerializer`, which compresses and stores (nearly) arbitrary python objects (see `serializer.ipynb`).

## The ConfigParser

The `ConfigParser` is a simple compiler that evaluates string substitutions within a YAML config file. Consider the following example config that assigns hex colors to fruits:

```yaml
fruits:
  apple: "{{colors.red}}"
  banana: "{{colors.yellow}}"
  orange: "{{colors.orange}}"
  strawberry: "{{colors.red}}"
  cherry: "{{colors.red}}"

colors:
  red: "#FF0000"
  yellow: "#FFFF00"
  orange: "#FFA500"
```

The syntax element `"{{colors.red}}"` denotes a string substitution that is evaluated by the `compile` method of the `ConfigParser`. The fruits section above will be evaluated to:

```yaml
fruits:
  apple: "#FF0000"
  banana: "#FFFF00"
  orange: "#FFA500"
  strawberry: "#FF0000"
  cherry: "#FF0000"
```

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



