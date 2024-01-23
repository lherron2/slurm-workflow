import re
import yaml
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        if isinstance(data, str):
            # Keep substituting until there are no more placeholders to substitute
            while True:
                new_data = self._substitute_variables(data)
                if new_data == data:  # No more substitutions were made
                    break
                data = new_data  # Update data with the substituted string
            return data
        elif isinstance(data, dict):
            substituted_data = {k: self._substitute_variables_recursive(v) for k, v in data.items()}
            return substituted_data
        elif isinstance(data, list):
            return [self._substitute_variables_recursive(v) for v in data]
        else:
            return data

    def _substitute_variables(self, data):
        flat_config_data = self._flatten_dict(self.config_data)
        if self.parent_config_data:
            flat_parent_config_data = self._flatten_dict(self.parent_config_data)
            flat_config_data = {**flat_parent_config_data, **flat_config_data}

        def replacer(match):
            key = match.group(1)
            if key not in flat_config_data:
                logging.warning(f"Key for substitution not found in config data: {key}")
            substitution = str(flat_config_data.get(key, match.group(0)))
            return substitution

        pattern = re.compile(r"{{([^}]+)}}")

        # Keep substituting until there are no more placeholders to substitute
        while True:
            new_data = pattern.sub(replacer, data)
            if new_data == data:  # No more substitutions were made
                break
            data = new_data

        return data
    
    def override_args(self, args):
        """
        Overrides the config_data with values from args.
        Args:
            args (dict): Dictionary of arguments to override.
        Returns:
            dict: Updated config_data.
        """
        for key, value in args.items():
            if key in self.config_data:
                # Assuming config_data is a nested dictionary and we need to apply get method of ConfigParser
                # We'll fetch the section and option from key and update the value accordingly
                section, option = key.split('.')  # Assuming key is in the format 'section.option'
                self.config_data[section][option] = self.get(section, option, fallback=value)
        return self.config_data

    
    def override_args(self, args_to_override):
        """
        Override configuration arguments.

        Args:
        args_to_override (dict): The arguments to override in the configuration.

        Returns:
        dict: The configuration data with overridden arguments.
        """
        def apply_overrides(item):
            if isinstance(item, dict):
                return {k: args_to_override.get(k, v) for k, v in item.items()}
            return item

        return self.traverse_and_apply(self.config_data, apply_overrides)


    # def override_args(self, args, subsection_paths=[]):
    #     args_dict = vars(args)

    #     if not subsection_paths:
    #         for arg_key in args_dict:
    #             config_value = self.get(arg_key)
    #             if config_value is not None:
    #                 args_dict[arg_key] = self._substitute_variables_recursive(config_value)
    #     else:
    #         for subsection_path in subsection_paths:
    #             subsection_data = self.get(subsection_path, {})
    #             if subsection_data:
    #                 for arg_key in args_dict:
    #                     config_value = self.get_from_subset(subsection_data, arg_key)
    #                     if config_value is not None:
    #                         args_dict[arg_key] = self._substitute_variables_recursive(config_value)
    #             else:
    #                 logging.info(f"Subsection '{subsection_path}' not found or is empty.")
    #     return argparse.Namespace(**args_dict)
    
    def set(self, key, value):
        keys = key.split('.')
        data = self.config_data

        for k in keys[:-1]:  # Traverse all keys except the last one
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]

        data[keys[-1]] = value

    def get(self, key, default=None):
        keys = key.split('.')
        data = self.config_data

        for k in keys:
            if isinstance(data, dict) and k in data:
                data = data[k]
            else:
                return default

        # Perform substitution only if data is a string
        if isinstance(data, str):
            data = self._substitute_variables_recursive(data)
        return data
    
    def compile(self, as_args=False, leaves=False):
        """
        Compile the entire configuration data by applying the get method to each key.

        Args:
            as_dict (bool): If True, return a dictionary, else return an argparse.Namespace object.

        Returns:
            A dictionary or argparse.Namespace object with the compiled configuration data.
        """
        compiled_data = {} # Defined here to allow recursive function to access it

        def compile_recursive(data, prefix=''):
            for k, v in data.items():
                full_key = f'{prefix}.{k}' if prefix else k
                if isinstance(v, dict):
                    compile_recursive(v, prefix=full_key)
                else:
                    compiled_data[full_key] = self.get(full_key)

        def create_nested_dict(flat_dict):
            """
            Convert a flat dictionary with dot-separated keys to a nested dictionary.
            flat_dict: The flat dictionary with dot-separated keys
            """
            nested = {}
            for key, value in flat_dict.items():
                keys = key.split('.')
                current_level = nested
                for part in keys[:-1]:
                    if part not in current_level:
                        current_level[part] = {}
                    current_level = current_level[part]
                current_level[keys[-1]] = value
            return nested

        def nested_dict_to_namespace(d):
            """
            Convert a nested dictionary to an argparse.Namespace recursively.
            d: The nested dictionary to convert
            """
            if not isinstance(d, dict):
                return d
            return argparse.Namespace(**{k: nested_dict_to_namespace(v) for k, v in d.items()}) 

        compile_recursive(self.config_data) # accesses compiled_data

        if leaves:
            compiled_data = {k.split('.')[-1]: v for k, v in compiled_data.items()}
        if not as_args:
            return compiled_data
        else:
            return nested_dict_to_namespace(create_nested_dict(compiled_data))
