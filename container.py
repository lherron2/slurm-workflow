from serializer import ObjectSerializer
from abc import ABC, abstractmethod
from typing import Optional
import argparse

class Process(ABC):
    """
    An abstract base class used to represent a Process.

    ...

    Attributes
    ----------
    name : str
        the name of the process

    Methods
    -------
    run():
        An abstract method that runs the process.
    handle_signal():
        An abstract method that handles the signal of the process.
    cleanup():
        An abstract method that cleans up after the process.
    """

    def __init__(self, name: str) -> None:
        """
        Initializes the Process with a name.

        Parameters:
        name (str): The name of the process.
        """
        self.name: str = name

    @abstractmethod
    def run(self) -> None:
        """An abstract method that runs the process."""
        pass

    @abstractmethod
    def handle_signal(self) -> None:
        """An abstract method that handles the signal of the process."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """An abstract method that cleans up after the process."""
        pass


class Container:
    """
    A class used to represent a Container for a Process.

    ...

    Attributes
    ----------
    process : Optional[Process]
        an instance of Process class

    Methods
    -------
    run():
        Runs the process.
    handle_signal():
        Handles the signal of the process.
    cleanup():
        Cleans up after the process.
    serialize(process: Process, path: str):
        Serializes the process and saves it to a file.
    load(path: str):
        Loads the process from a file.
    execute(path: str):
        Executes the process from a file.
    """

    def __init__(self, process: Optional[Process] = None) -> None:
        """Initializes the Container with no process."""
        self.process = process

    def run_process(self) -> None:
        """
        Runs the process if it has a 'run' method.

        This method checks if the 'process' object has a 'run' method. If it does, it calls the 'run' method.
        If it doesn't, it raises an AttributeError with a suitable error message.
        """
        if hasattr(self.process, 'run'):
            self.process.run()
        else:
            raise AttributeError("'process' object has no attribute 'run'")

    def handle_signal(self) -> None:
        """Handles the signal of the process."""
        self.process.handle_signal()

    def cleanup(self) -> None:
        """Cleans up after the process."""
        self.process.cleanup()

    def serialize(self, path: str) -> None:
        """
        Serializes the process and saves it to a file.

        Parameters:
        process (Process): The process to serialize.
        path (str): The path to the file where the serialized process will be saved.
        """
        ObjectSerializer(path).serialize(self.process, overwrite=True)

    def load(self, path: str) -> None:
        """
        Loads the process from a file.

        Parameters:
        path (str): The path to the file where the serialized process is stored.
        """
        OS = ObjectSerializer(path)
        self.process = OS.load()

    def run(self, path: str) -> None:
        """
        Executes the process from a file.

        Parameters:
        path (str): The path to the file where the serialized process is stored.
        """
        self.load(path)
        self.run_process()
        self.handle_signal()
        self.cleanup()

    @staticmethod
    def handle_command_line() -> None:
        '''Handles command line arguments for the Container class.'''
        parser = argparse.ArgumentParser(description='Container Process Runner')
        parser.add_argument('command', choices=['run'], help='Command to execute')
        parser.add_argument('path', type=str, help='Path to the serialized container file')
        args = parser.parse_args()

        if args.command == 'run':
            container = Container()
            container.execute(args.path)

if __name__ == "__main__":
    Container.handle_command_line()