# Database Module README

## Overview

The Database module is a sophisticated integration of file handling and configuration management. It blends features from ObjectSerializer (OS) and slurm-config (SC) to offer a versatile, filesystem-like data management tool. This module allows hierarchical data storage and retrieval with advanced pattern matching capabilities.

## Key Components

### StructuredStorage

StructuredStorage serves as the foundation for data storage, with subclasses for different storage formats.

#### Subclasses

- **YAMLStorage**: Handles YAML file format.
- **H5Storage**: Manages data in an h5 file format.

### YAMLStorage Class

The YAMLStorage class in the Database module is designed to manage YAML-formatted configuration files. It reads and writes data to and from YAML files, treating the data as dictionaries.

#### Features

- Reads YAML files into a dictionary.
- Writes dictionary data back to YAML files.
- Maintains two dictionaries:
    - One for the raw YAML file contents.
    - Another for the compiled contents after processing through the Syntax class.

#### Implementation

```python
import yaml

class YAMLStorage:
    def __init__(self, filepath):
        self.filepath = filepath
        self.raw_data = {}
        self.compiled_data = {}

    def read(self):
        with open(self.filepath, 'r') as file:
            self.raw_data = yaml.safe_load(file) or {}
            self.compiled_data = self.raw_data.copy()  # Initially, compiled_data is a copy of raw_data

    def write(self):
        with open(self.filepath, 'w') as file:
            yaml.dump(self.compiled_data, file)

    def get_raw_data(self):
        return self.raw_data

    def get_compiled_data(self):
        return self.compiled_data

    def update_compiled_data(self, new_data):
        self.compiled_data = new_data
```

#### Usage

The YAMLStorage class is used within the Database module to manage the configuration data. After reading the YAML file, it keeps the raw data untouched for reference, while the compiled data can be modified as needed, particularly after being processed by the Syntax class.

### H5Storage Class

The H5Storage class is tailored for managing data in h5 file formats, drawing inspiration from the ObjectSerializer module you provided. It includes methods for saving and retrieving various types of data, including arrays and serialized objects.

#### Features

- Handles h5 file format for data storage.
- Capable of storing and retrieving a wide range of data types.
- Excludes syntactical handling, focusing solely on data serialization and deserialization.

#### Implementation

```python
import h5py
import numpy as np
import dill

class H5Storage:
    def __init__(self, filepath):
        self.filepath = filepath

    def save(self, path, data):
        with h5py.File(self.filepath, 'a') as file:
            if isinstance(data, np.ndarray):
                file[path] = data
            else:
                # Use dill to serialize non-numpy data
                file[path] = np.void(dill.dumps(data))

    def load(self, path):
        with h5py.File(self.filepath, 'r') as file:
            data = file[path][()]
            if isinstance(data, np.void):
                # Deserialize if data is not a numpy array
                return dill.loads(data.tostring())
            return data
```

#### Usage

H5Storage is utilized within the Database module for efficient storage and retrieval of data in h5 format. It simplifies the process of storing complex data structures and arrays, ensuring they are easily accessible when required.

### Syntax Class

The Syntax class is a sophisticated component of the Database module, designed to handle complex string operations and pattern matching. It will facilitate the interpretation of path-like structures and enable advanced string manipulation techniques.

#### Features

- Globbing: Allows for flexible pattern matching in paths.
- Dot Path Notation: Interprets and resolves paths using dot-separated strings.
- Pattern Matching: Utilizes regular expressions to match and filter paths.
- Recursive String Substitution: Implements recursive replacement of placeholders in strings.

#### Implementation

```python
import re
import fnmatch

class Syntax:
    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, path):
        # Pattern matching using regular expressions
        return re.match(self.pattern, path)

    def glob_match(self, path, pattern):
        # Globbing pattern matching
        return fnmatch.fnmatch(path, pattern)

    def dot_path_resolver(self, path, data_dict):
        # Resolves dot path notation to access nested dictionary data
        keys = path.split('.')
        return reduce(lambda d, key: d.get(key, None) if isinstance(d, dict) else None, keys, data_dict)

    def recursive_substitute(self, string, data_dict):
            # Recursive string substitution
            def replacer(match):
                key = match.group(1)
                return str(self.dot_path_resolver(key, data_dict)) if key in data_dict else match.group(0)
    
            old_string = None
            while old_string != string:
                old_string = string
                string = re.sub(r'{(.+?)}', replacer, string)
            return string
```

#### Usage

The Syntax class will be used in conjunction with the YAMLStorage and H5Storage classes for path resolution and string manipulation. It enables the Database module to interpret complex paths and patterns, enhancing the module's flexibility and capability.

- Globbing: To match files or paths based on specified patterns.
- Dot Path Notation: For accessing nested data within the stored configuration or data files.
- Recursive String Substitution: To dynamically replace placeholders in configuration strings, based on other configuration values.

### Database Class

The Database class is the central component of the module, designed to interact with a specific data storage format (YAML or h5) and handle complex path and string manipulations.
Design

- Inherits from one StructuredStorage subclass (YAMLStorage or H5Storage) and the Syntax class.
- Manages data storage and retrieval operations.
- Processes complex path and string patterns using Syntax.

#### Implementation

```python

class Database(StructuredStorage, Syntax):
    def __init__(self, storage, syntax):
        StructuredStorage.__init__(self, storage.filepath)
        Syntax.__init__(self, syntax.pattern)
        self.storage = storage
        self.syntax = syntax

    def add_entry(self, path, data):
        if self.syntax.match(path) or self.syntax.glob_match(path, self.syntax.pattern):
            self.storage.update_compiled_data({path: data})
            self.storage.write()

    def get_entry(self, path):
        if self.syntax.match(path) or self.syntax.glob_match(path, self.syntax.pattern):
            return self.storage.get_compiled_data()[path]
        else:
            raise ValueError("Path does not match syntax patterns")
```

#### Usage
- Adding Data: To add an entry to the database, the add_entry method takes a path and data. The path is validated and processed using the Syntax class.
- Retrieving Data: The get_entry method retrieves data from the database using a given path, which is also validated and processed through the Syntax class.

#### Example of Database Usage

```python
import YAMLStorage, Syntax
yaml_storage = YAMLStorage('config.yaml')
syntax = Syntax(r'path.to.\w+')

# Creating a Database instance with YAMLStorage and Syntax
db = Database(yaml_storage, syntax)

# Adding data to the database
db.add_entry('path.to.setting', {'key': 'value'})

# Retrieving data from the database
data = db.get_entry('path.to.setting')
print(data)  # Output: {'key': 'value'}
```

This example demonstrates how to initialize the `Database` class with `YAMLStorage` and `Syntax`, add an entry to the database, and then retrieve it. The `Database` class seamlessly integrates the functionalities of its constituent classes, providing a unified interface for data storage and retrieval with advanced path and string processing capabilities.
