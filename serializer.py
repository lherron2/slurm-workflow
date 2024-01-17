import h5py
import blosc
import os
import dill
import numpy as np
from typing import Any
import importlib

import logging

logging.basicConfig(
    level=logging.DEBUG,  # Set log level to DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',  # Define the log format
    datefmt='%Y-%m-%d %H:%M:%S'  # Define the date format
)
logger = logging.getLogger()

class ObjectSerializer:
    def __init__(self, filename: str):
        self.filename = filename

    def print_summary(self) -> None:
        """
        Print a summary of the contents of the HDF5 file.

        This method opens the HDF5 file in read mode and visits each group and dataset in the file, printing its name.

        Returns:
        None
        """
        with h5py.File(self.filename, 'r') as hdf_file:
            hdf_file.visit(print)

    def compress_data(self, data: bytes, chunksize: int = 1024*1024) -> bytes:
        """
        Compress data in chunks using Blosc.

        This method compresses the input data using Blosc and returns the compressed data.

        Parameters:
        data (bytes): The data to compress.
        chunksize (int, optional): The chunk size to use for compression. Defaults to 1024*1024.

        Returns:
        bytes: The compressed data.
        """
        compressed_data = blosc.compress(data)
        return bytes(compressed_data)

    def decompress_data(self, data: bytes, chunksize: int = 1024*1024) -> bytes:
        """
        Decompress data in chunks using Blosc.

        This method decompresses the input data using Blosc and returns the decompressed data.

        Parameters:
        data (bytes): The data to decompress.
        chunksize (int, optional): The chunk size to use for decompression. Defaults to 1024*1024.

        Returns:
        bytes: The decompressed data.
        """
        decompressed_data = blosc.decompress(data)
        return bytes(decompressed_data)

    def ensure_path_exists(self, hdf_file: h5py.File, path: str) -> None:
        """
        Ensure all groups in the path exist in the HDF5 file.

        This method splits the path into parts and iterates over them. For each part, it checks if a group with that name exists at the current path in the HDF5 file. If not, it creates a new group.

        Parameters:
        hdf_file (h5py.File): The HDF5 file to check.
        path (str): The path to ensure exists.

        Returns:
        None
        """
        path_parts = path.split('/')
        current_path = ''
        for part in path_parts:
            if part:  # Check if part is not an empty string
                current_path += '/' + part
                if current_path not in hdf_file:
                    hdf_file.create_group(current_path)
                    
    def serialize(self, obj: Any, path: str = '/', overwrite: bool = False) -> None:
        """
        Recursively store an object and its nested objects in the HDF5 file.

        This method serializes and compresses the object and its attributes, 
        and stores them in the HDF5 file at the specified path. It handles
        nested objects and stores their paths and types for reconstruction.
        """

        if overwrite and os.path.exists(self.filename):
            os.remove(self.filename)

        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        with h5py.File(self.filename, 'a') as hdf_file:
            self.ensure_path_exists(hdf_file, path)
            self._recursive_store(hdf_file, obj, path)

    def _recursive_store(self, hdf_file: h5py.File, obj: Any, current_path: str) -> None:
        """
        Recursively stores an object and its attributes in an HDF5 file.

        This method checks if the object has a __dict__ attribute. If it does, it stores the type of the object and 
        recursively stores all its attributes. If it doesn't, it serializes the object and stores it directly.

        Args:
            hdf_file (h5py.File): The HDF5 file to store the object in.
            obj (Any): The object to store.
            current_path (str): The current path in the HDF5 file.

        Returns:
            None
        """
        logger.debug(f"Storing object at path: {current_path}")
        if hasattr(obj, '__dict__'):
            class_name = type(obj).__module__ + '.' + type(obj).__name__
            if current_path not in hdf_file:
                logger.debug(f"Creating new group at path: {current_path}")
                hdf_file.create_group(current_path)
            else:
                logger.debug(f"Path already exists at: {current_path}")
            hdf_file[current_path].attrs['type'] = class_name

            for attr_name, attr_value in obj.__dict__.items():
                attr_path = f'{current_path}/{attr_name}'
                logger.debug(f"Processing attribute: {attr_name}, path: {attr_path}")
                self._recursive_store(hdf_file, attr_value, attr_path)
        else:
            logger.debug(f"Object does not have a __dict__. Serializing and storing directly at path: {current_path}")
            serialized_data = dill.dumps(obj)
            try:
                compressed_data = blosc.compress(serialized_data)
                data_to_store = np.void(compressed_data)
            except TypeError:
                data_to_store = np.void(serialized_data)

            if current_path in hdf_file and current_path != '/':
                logger.debug(f"Deleting existing object at path: {current_path} to create a new dataset")
                del hdf_file[current_path]

            hdf_file.create_dataset(current_path, data=data_to_store)

    def load(self, path: str = '/') -> Any:
        """
        Recursively load an object and its nested objects from the HDF5 file.

        This method loads an object from the specified path, reconstructing
        it and its nested objects by deserializing and decompressing the stored data.
        """
        with h5py.File(self.filename, 'r') as hdf_file:
            return self._recursive_load(hdf_file, path)
    
    def _recursive_load(self, hdf_file: h5py.File, current_path: str) -> Any:
        """
        Recursively load an object from the HDF5 file.

        This private method is called by the public load method. It handles the 
        deserialization and reconstruction of objects stored in the HDF5 file, 
        including nested objects.

        Parameters:
        hdf_file (h5py.File): The HDF5 file to read from.
        current_path (str): The current path in the HDF5 file from which to load the object.

        Returns:
        Any: The reconstructed object.
        """
        if current_path not in hdf_file:
            raise ValueError(f"Path {current_path} does not exist in the HDF5 file.")

        # Check if the current path is a dataset or a group (object with __dict__)
        if isinstance(hdf_file[current_path], h5py.Dataset):
            # It's a dataset, so load and deserialize the data
            serialized_data = hdf_file[current_path][()]
            try:
                # Attempt to decompress, assuming data is blosc compressed
                decompressed_data = blosc.decompress(serialized_data)
            except TypeError:
                # If decompression fails, assume data was stored as is
                decompressed_data = serialized_data
            return dill.loads(decompressed_data)
        else:
            # It's a group, so treat it as an object with __dict__
            class_name = hdf_file[current_path].attrs['type']
            module_name, class_name = class_name.rsplit('.', 1)
            module = importlib.import_module(module_name)
            obj_type = getattr(module, class_name)
            obj = obj_type.__new__(obj_type)

            for attr_name in hdf_file[current_path].keys():
                attr_path = f'{current_path}/{attr_name}'.lstrip('/')
                nested_obj = self._recursive_load(hdf_file, attr_path)
                setattr(obj, attr_name, nested_obj)

            return obj