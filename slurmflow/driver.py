import os
import time
import subprocess
import tempfile

from typing import List, Dict, Optional
from . import logger



class SlurmDriver:
    """
    A driver class for managing Slurm jobs.

    This class provides an interface for creating, submitting, and managing Slurm jobs.
    It checks if Slurm is available on the system and maintains a registry of jobs.

    Attributes:
        slurm_available (bool): Indicates if Slurm is available on the system.
        jobs_registry (dict): A dictionary to keep track of jobs.
    """

    def __init__(self, verbose=False) -> None:
        """
        Initializes the SlurmDriver with the availability of Slurm and an empty jobs registry.
        """
        self.slurm_available: bool = self._is_slurm_available()
        self.jobs_registry: dict = {}
        self.verbose = verbose

    def _is_slurm_available(self) -> bool:
        """
        Checks if Slurm is available on the system by running 'sbatch --version' 
        and checking if 'slurm' is in the output.

        Returns:
            bool: True if Slurm is available, False otherwise.
        """
        try:
            result = subprocess.run(
                ["sbatch", "--version"], capture_output=True, text=True
            )
            return "slurm" in result.stdout
        except Exception:
            return False

    def generate_slurm_args(self, **kwargs) -> str:
        """
        Generates the Slurm job submission arguments based on the 
        provided keyword arguments. It ensures that the arguments are in the 
        correct format for Slurm.

        Args:
            **kwargs: Arbitrary keyword arguments that represent Slurm job parameters.

        Returns:
            A string containing Slurm job submission arguments.
        """
        args = {
            "partition": "standard",
            "ntasks": 1,
            "cpus_per_task": 1,
            "mem": "8G",
            "time": "1:00:00",
            "job_name": "python_job",
        }
        args.update(kwargs)


        output_path = os.path.join(args.get("output_dir", ""), f'slurm_{args["job_name"]}.out')
        error_path = os.path.join(args.get("output_dir", ""), f'slurm_{args["job_name"]}.err')

        slurm_args = []
        args.pop("output_dir")
        for key, value in args.items():
            if key != 'gres':
                slurm_key = key.replace('_', '-')
                slurm_args.append(f"#SBATCH --{slurm_key}={value}")

        slurm_args.append(f"#SBATCH --output={output_path}")
        slurm_args.append(f"#SBATCH --error={error_path}")

        if "gres" in kwargs:
            slurm_args.append(f"#SBATCH --gres={kwargs['gres']}")

        slurm_args_str = "\n".join(slurm_args)

        return slurm_args_str, output_path, error_path
 
    def create_output_directory(self, output_dir: str) -> None:
        """
        Creates the output directory for Slurm job files.

        This method creates the specified directory if it doesn't exist. 
        It handles any exceptions related to directory creation and logs them.

        Args:
            output_dir (str): The path to the output directory to be created.

        Returns:
            None
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"Failed to create directory {output_dir}. Error: {e}")


    def cancel_job(self, job_id: str) -> str:
        """
        Cancels a Slurm job with the given job ID.

        This method runs the 'scancel' command with the provided job ID and 
        returns the output of the command.

        Args:
            job_id (str): The ID of the Slurm job to be cancelled.

        Returns:
            str: The output of the 'scancel' command.
        """
        result = subprocess.run(["scancel", job_id], capture_output=True, text=True)
        return result.stdout

    def list_jobs(self, state: Optional[str] = None) -> List[str]:
        """
        Lists the Slurm jobs with the given state.

        This method runs the 'squeue' command with the provided state (if any) and 
        returns the IDs of the jobs as a list of strings.

        Args:
            state (str, optional): The state of the Slurm jobs to be listed. Defaults to None.

        Returns:
            List[str]: The IDs of the Slurm jobs in the given state.
        """
        cmd = ["squeue", "-h", "-o", "%i"]
        if state:
            cmd.extend(["-t", state])
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.splitlines()

    def submit_job(self, cmd: str, slurm_args: Dict[str, str] = {}, env: Optional[str] = None, modules: List[str] = [],  track: bool = True, venv='mamba') -> str:
        """
        Submits a Slurm job with the given parameters.

        This method generates the Slurm arguments, creates the output and error directories,
        creates the script for the job, and submits the job. It also registers the job in the jobs registry.

        Args:
            container_path (str): The path to the container for the job.
            conda_env (str, optional): The conda environment to use. Defaults to None.
            modules (List[str], optional): The modules to load. Defaults to [].
            slurm_args (Dict[str, str], optional): The Slurm arguments. Defaults to {}.

        Returns:
            str: The ID of the submitted job.
        """
        slurm_args, output_path, error_path = self.generate_slurm_args(**slurm_args)
        logger.debug(slurm_args)
        self.create_output_directory(os.path.dirname(output_path))
        self.create_output_directory(os.path.dirname(error_path))
        script_content = self._create_script(cmd, slurm_args, env, modules, venv)
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.sh') as tmpfile:
            tmpfile.write(script_content)
            tmpfile_path = tmpfile.name

        result = subprocess.run(['sbatch', tmpfile_path], capture_output=True, text=True)
        job_id = result.stdout.strip().split()[-1]
        logger.debug(job_id)
        if track:
            self.jobs_registry[job_id] = {'status': 'submitted', 'script': tmpfile_path}
        return job_id

    def check_job_status(self, job_id: str) -> str:
        """
        Checks the status of a Slurm job with the given job ID.

        This method runs the 'squeue' command with the provided job ID and 
        updates the status of the job in the jobs registry. If the job ID is not 
        in the jobs registry, it returns 'unknown job id'.

        Args:
            job_id (str): The ID of the Slurm job to check.

        Returns:
            str: The status of the job.
        """
        if job_id in self.jobs_registry:
            result = subprocess.run(['squeue', '-j', job_id], capture_output=True, text=True)
            if 'PD' in result.stdout:  # Pending
                self.jobs_registry[job_id]['status'] = 'pending'
            elif 'R' in result.stdout:  # Running
                self.jobs_registry[job_id]['status'] = 'running'
            else:
                self.jobs_registry[job_id]['status'] = 'completed'
            return self.jobs_registry[job_id]['status']
        else:
            return 'unknown job id'

    def refresh_registry(self, clear_completed: bool = False) -> Dict[str, Dict[str, str]]:
        """
        Checks the status of all Slurm jobs in the jobs registry and optionally removes completed or failed jobs.

        This method iterates over all job IDs in the jobs registry and checks 
        their status by calling the check_job_status method. If remove_completed_failed is True, 
        it removes jobs with 'completed' or 'failed' status from the registry. It returns the updated 
        jobs registry.

        Args:
            remove_completed_failed (bool): If True, removes jobs with 'completed' or 'failed' status from the registry.

        Returns:
            Dict[str, Dict[str, str]]: The updated jobs registry with the status of all jobs.
        """
        job_ids = list(self.jobs_registry.keys())  # Create a copy of keys to iterate over
        for job_id in job_ids:
            status = self.check_job_status(job_id)
            if clear_completed and status in ['completed']:
                del self.jobs_registry[job_id]
        return self.jobs_registry

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancels a Slurm job with the given job ID.

        This method runs the 'scancel' command with the provided job ID and 
        updates the status of the job in the jobs registry to 'cancelled'. If the 
        job ID is not in the jobs registry, it returns False.

        Args:
            job_id (str): The ID of the Slurm job to be cancelled.

        Returns:
            bool: True if the job was successfully cancelled, False otherwise.
        """
        if job_id in self.jobs_registry:
            subprocess.run(['scancel', job_id])
            self.jobs_registry[job_id]['status'] = 'cancelled'
            return True
        else:
            return False

    def _create_script(self, cmd: str, slurm_args: List[str], env: str, modules: List[str], venv: str) -> str:
        """
        Creates a script for a Slurm job with the given parameters.

        This method generates the script lines based on the provided parameters, 
        joins them with newline characters, and returns the resulting string.

        Args:
            container_path (str): The path to the container for the job.
            conda_env (str, optional): The conda environment to use. Defaults to None.
            modules (List[str]): The modules to load.
            slurm_args (Dict[str, str]): The Slurm arguments.

        Returns:
            str: The script for the Slurm job.
        """
        script_lines = ["#!/bin/bash"]
        if slurm_args:
            script_lines.append(slurm_args)
        if env:
            if venv == 'mamba':
                script_lines.append("source $MAMBA_ROOT_PREFIX/etc/profile.d/micromamba.sh")
                script_lines.append(f"micromamba activate {env}")
            elif venv == 'conda':
                script_lines.append("""__conda_setup="$('conda' 'shell.bash' 'hook' 2> /dev/null)""")
                script_lines.append("""eval "$__conda_setup""")
                script_lines.append("""unset __conda_setup""")
                script_lines.append(f"conda activate {env}")
            else:
                raise ValueError(f"Unknown venv: {venv}")
        if modules:
            for module in modules:
                script_lines.append(f"module load {module}")
        script_lines.append(f"{cmd}")
        if self.verbose:
            logger.info(script_lines)
        return "\n".join(script_lines)
    
    def wait(self, sleep_time: int = 10) -> None:
        """
        Waits for all Slurm jobs in the jobs registry to complete.

        This method iterates over all job IDs in the jobs registry and checks 
        their status by calling the check_job_status method. It waits until all 
        jobs have 'completed' status.

        Returns:
            None
        """
        # Get a list of all job IDs in the jobs registry
        job_ids = list(self.jobs_registry.keys())
        
        # Start an infinite loop
        while True:
            # Iterate over each job ID after a sleep time
            time.sleep(sleep_time)
            for job_id in job_ids:
                # Check the status of the current job
                status = self.check_job_status(job_id) 
                # If the job status is not 'completed', break the loop
                if status != 'completed':
                    break
            else:
                # If all jobs have 'completed' status, break the infinite loop
                break
