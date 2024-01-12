from container import Process, Container
from driver import SLURMDriver
import numpy as np
import time
import os

class ArrayProcess(Process):
    def __init__(self, name: str, filename: str):
        super().__init__(name)
        self.filename = filename

    def run(self) -> None:
        array = np.array([1, 2, 3, 4, 5])
        np.save(self.filename, array)
        print(f"Array saved to {self.filename}")

    def handle_signal(self) -> None:
        pass

    def cleanup(self) -> None:
        pass

# Example usage
if __name__ == "__main__":
    array_process = ArrayProcess('ArrayProcess', 'output.npy')

    container = Container(array_process)
    container.serialize('test_container.h5')

    driver = SLURMDriver()

    slurm_args = {'partition': 'standard',
                  'cpus-per-task': '1', 
                  'mem': '2G', 
                  'time': '01:00:00'}

    job_id = driver.submit_job('test_container.h5', slurm_args=slurm_args)
    status = driver.check_job_status(job_id)

    while status != 'completed':
        time.sleep(10)  # Wait for 10 seconds
        status = driver.check_job_status(job_id)

    # Check if the file exists
    if os.path.exists('output.npy'):
        array = np.load('output.npy')
        expected_array = np.array([1, 2, 3, 4, 5])
        if np.array_equal(array, expected_array):
            print("The file contains the expected array.")
        else:
            print("The file does not contain the expected array.")
    else:
        print("The file does not exist.")