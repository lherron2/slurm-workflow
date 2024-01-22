import re
import yaml
import logging
import argparse
from collections import ChainMap

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def substitute_string(data, key, value):
    # Define a replacer function
    def replacer(match):
        k = match.group(1)
        if k == key:
            return str(value)
        return match.group(0)

    # Perform substitution until no more placeholders can be substituted
    while True:
        new_data, n = re.subn(r'{{(.*?)}}', replacer, data)
        logging.debug(f"Substituting '{data}' with '{new_data}'")
        if n == 0:
            break
        data = new_data

    return data

class ConfigParser:

    def __init__(self, config_source, parent_config_data=None):
        self.parent_config_data = parent_config_data
        self.config_data = None
        if isinstance(config_source, str):
            self._load_config_from_file(config_source)
        elif isinstance(config_source, dict):
            self.config_data = config_source
        else:
            raise ValueError("Invalid config source type. Must be filename (str) or config data (dict).")

    def _load_config_from_file(self, config_file):
        with open(config_file, 'r') as file:
            self.config_data = yaml.safe_load(file)
#        self.config_data = self._substitute_variables_recursive(self.config_data)

    def _flatten_dict(self, d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _substitute_variables_recursive(self, data):
        logging.debug(f"Starting recursive substitution for data: {data}")
        if isinstance(data, str):
            # Keep substituting until there are no more placeholders to substitute
            while True:
                new_data = self._substitute_variables(data)
                if new_data == data:  # No more substitutions were made
                    logging.debug(f"No more substitutions possible for: {data}")
                    break
                data = new_data  # Update data with the substituted string
                logging.debug(f"Data after substitution: {data}")
            return data
        elif isinstance(data, dict):
            substituted_data = {k: self._substitute_variables_recursive(v) for k, v in data.items()}
            return substituted_data
        elif isinstance(data, list):
            return [self._substitute_variables_recursive(v) for v in data]
        else:
            return data

    def _substitute_variables(self, data):

        logging.debug(f"Substituting variables in data: {data}")
        flat_config_data = self._flatten_dict(self.config_data)

        if self.parent_config_data:
            flat_parent_config_data = self._flatten_dict(self.parent_config_data)
            flat_config_data = {**flat_parent_config_data, **flat_config_data}

        logging.debug(f"Flat config data for substitution: {flat_config_data}")

        def replacer(match):
            key = match.group(1)
            if key not in flat_config_data:
                logging.warning(f"Key for substitution not found in config data: {key}")
            substitution = str(flat_config_data.get(key, match.group(0)))
            logging.debug(f"Substituting '{match.group(0)}' with '{substitution}'")
            return substitution

        pattern = re.compile(r"{{([^}]+)}}")

        # Keep substituting until there are no more placeholders to substitute
        while True:
            new_data = pattern.sub(replacer, data)
            if new_data == data:  # No more substitutions were made
                break
            data = new_data
            logging.debug(f"Data after regex substitution: {data}")

        return data

    def get_sub_config(self, section_paths):
        sub_configs = [self.get(path, {}) for path in section_paths]

        merged_config = dict(ChainMap(*sub_configs))
        return ConfigParser(merged_config, parent_config_data=self.config_data)

    def override_args(self, args, subsection_paths=[]):
        logging.debug("Starting to override args.")
        args_dict = vars(args)

        if not subsection_paths:
            logging.debug("No subsection paths provided; searching through the entire config.")
            for arg_key in args_dict:
                config_value = self.get(arg_key)
                if config_value is not None:
                    logging.debug(f"Overriding arg '{arg_key}' with config value from the entire config.")
                    args_dict[arg_key] = self._substitute_variables_recursive(config_value)
        else:
            for subsection_path in subsection_paths:
                logging.debug(f"Searching in subsection '{subsection_path}'.")
                subsection_data = self.get(subsection_path, {})
                if subsection_data:
                    for arg_key in args_dict:
                        config_value = self.get_from_subset(subsection_data, arg_key)
                        if config_value is not None:
                            logging.debug(f"Overriding arg '{arg_key}' with config value from subsection '{subsection_path}'.")
                            args_dict[arg_key] = self._substitute_variables_recursive(config_value)
                else:
                    logging.debug(f"Subsection '{subsection_path}' not found or is empty.")

        logging.debug("Finished overriding args.")
        logging.debug(f"Overridden args: {args_dict}")
        return argparse.Namespace(**args_dict)
    
    def get_from_subset(self, config_subset, key):
        logging.debug(f"Retrieving value for key '{key}' from config subset.")
        keys = key.split('.')
        data = config_subset

        for k in keys:
            if isinstance(data, dict):
                if k in data:
                    data = data[k]
                    logging.debug(f"Found key '{k}'; descending into nested config.")
                else:
                    # Search recursively in each dictionary value
                    for sub_key, sub_value in data.items():
                        if isinstance(sub_value, dict):
                            result = self.get_from_subset(sub_value, k)
                            if result is not None:
                                return result
                    logging.debug(f"Key '{k}' not found in this config subset.")
                    return None
            else:
                logging.debug(f"Non-dict type encountered; cannot search further for '{k}'.")
                return None

        if isinstance(data, str):
            logging.debug(f"Performing substitution for string data: {data}")
            data = self._substitute_variables_recursive(data)
            logging.debug(f"Substitution result: {data}")

        logging.debug(f"Returning data for key '{key}': {data}")
        return data

    def _recursive_search(self, d, target_key):
        """
        Recursively search for a key in a dictionary.

        :param d: Dictionary or any other datatype.
        :param target_key: Target key to search for.
        :return: Value of the key if found, otherwise None.
        """
        if isinstance(d, dict):
            for key, value in d.items():
                if key == target_key:
                    return value
                result = self._recursive_search(value, target_key)
                if result is not None:
                    return result
        return None

    def set(self, key, value):
        logging.debug(f"Setting value: {value} for key: {key}")
        keys = key.split('.')
        data = self.config_data

        for k in keys[:-1]:  # Traverse all keys except the last one
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
                logging.debug(f"Creating sub-dictionary for key: {k}")
            data = data[k]

        logging.debug(f"Setting the final key '{keys[-1]}' with value: {value}")
        data[keys[-1]] = value

    def get(self, key, default=None):
        logging.debug(f"Retrieving value for key: {key}")
        keys = key.split('.')
        data = self.config_data

        for k in keys:
            if isinstance(data, dict) and k in data:
                data = data[k]
                logging.debug(f"Key '{k}' found, moving to sub-dictionary or final value.")
            else:
                logging.debug(f"Key '{k}' not found, returning default value: {default}")
                return default

        # Perform substitution only if data is a string
        if isinstance(data, str):
            logging.debug(f"Data is a string, performing substitution for: {data}")
            data = self._substitute_variables_recursive(data)
        else:
            logging.debug(f"Data for key '{key}' is not a string, returning as is.")

        logging.debug(f"Returning data for key '{key}': {data}")
        return data
