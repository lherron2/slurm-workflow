import h5py
import blosc2
import os
import dill
import numpy as np
from typing import Any
import importlib
from . import logger

class ObjectSerializer:
    def __init__(self, **kwargs):
        pass

    def print_summary(self, filename, chunks=False) -> None:
        """
        Print a summary of the contents of the HDF5 file.

        This method opens the HDF5 file in read mode and visits each group and dataset in the file, printing its name.

        Returns:
        None
        """
        def print_no_chunks(name):
            if 'chunk_' not in name:
                print(name)

        with h5py.File(filename, 'r') as hdf_file:
            if chunks:
                hdf_file.visit(print)
            else:
                hdf_file.visit(print_no_chunks)
            
    def compress_data(self, data: Any, chunksize: int = 10_000_000) -> [bytes]:
        serialized_data = dill.dumps(data)
        schunk = blosc2.SChunk(chunksize=chunksize)
        for i in range(len(serialized_data) // chunksize + 1):
            schunk.append_data(serialized_data[i*chunksize:(i+1)*chunksize])
        cframe = schunk.to_cframe()

        # Chunk the cframe for HDF5 storage
        cframe_chunks = [cframe[i:i + chunksize] for i in range(0, len(cframe), chunksize)]
        return cframe_chunks

    def decompress_data(self, concatenated_cframe: [bytes]) -> Any:
        reconstructed_schunk = blosc2.schunk_from_cframe(concatenated_cframe)
        decompressed_data = b''.join(reconstructed_schunk.decompress_chunk(i) 
                                     for i in range(reconstructed_schunk.nchunks))
        return dill.loads(decompressed_data)

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
                    
    def save(self, obj: Any, filename: str, internal_path: str = '/', overwrite: bool = True) -> None:
        """
        Recursively store an object and its nested objects in the HDF5 file.

        This method serializes and compresses the object and its attributes, 
        and stores them in the HDF5 file at the specified path. It handles
        nested objects and stores their paths and types for reconstruction.
        """

        if overwrite and os.path.exists(filename):
            os.remove(filename)

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with h5py.File(filename, 'a') as hdf_file:
            self.ensure_path_exists(hdf_file, internal_path)
            self._recursive_store(hdf_file, obj, internal_path)

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
        if hasattr(obj, '__dict__') and  bool(obj.__dict__):
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
            cframe_chunks = self.compress_data(serialized_data)

            if current_path in hdf_file and current_path != '/':
                logger.debug(f"Deleting existing object at path: {current_path} to create a new dataset")
                del hdf_file[current_path]
                
            for i, chunk in enumerate(cframe_chunks):
                hdf_file.create_dataset(f"{current_path}/chunk_{i}", data=np.void(chunk))

    def load(self, filename: str, internal_path: str = '/') -> Any:
        """
        Recursively load an object and its nested objects from the HDF5 file.

        This method loads an object from the specified path, reconstructing
        it and its nested objects by deserializing and decompressing the stored data.
        """
        with h5py.File(filename, 'r') as hdf_file:
            return self._recursive_load(hdf_file, internal_path)
    
    def _recursive_load(self, hdf_file: h5py.File, current_path: str) -> Any:
        if current_path not in hdf_file:
            raise ValueError(f"Path {current_path} does not exist in the HDF5 file.")

        # Check if the current path is a dataset or a group
        if isinstance(hdf_file[current_path], h5py.Group) and 'type' in hdf_file[current_path].attrs:
            # It's a group, so treat it as an object with __dict__
            class_name = hdf_file[current_path].attrs['type']
            module_name, class_name = class_name.rsplit('.', 1)
            module = importlib.import_module(module_name)
            obj_type = getattr(module, class_name)
            obj = obj_type.__new__(obj_type)

            for attr_name in hdf_file[current_path].keys():
                # Exclude special attributes like '__dict__'
                if not attr_name.startswith('__'):
                    attr_path = f'{current_path}/{attr_name}'.lstrip('/')
                    nested_obj = self._recursive_load(hdf_file, attr_path)
                    setattr(obj, attr_name, nested_obj)

            return obj
        else:
            # It's a dataset, so load and deserialize the data
            serialized_data = []
            i = 0
            while f'{current_path}/chunk_{i}' in hdf_file:
                chunk = hdf_file[f'{current_path}/chunk_{i}'][()].tobytes()
                serialized_data.append(chunk)
                i += 1
            concatenated_data = b''.join(serialized_data)
            try:
                decompressed_data = self.decompress_data(concatenated_data)
            except TypeError:
                decompressed_data = concatenated_data
            return dill.loads(decompressed_data)
