# SLURMDriver: Advanced Task Management for Distributed Computing

Welcome to the SLURMDriver section of our distributed computing framework using Python and SLURM. The SLURMDriver class is designed to efficiently manage, monitor, and control the execution of computational tasks in high-performance computing clusters. This class facilitates the streamlined management of tasks, including support for containerized applications with customizable environments and SLURM job scheduling parameters.

## SLURMDriver: Enhanced Job Management and Monitoring

The SLURMDriver serves as a crucial interface to the SLURM job scheduler. It now offers extended capabilities for job submissions, including running containers with specific environment configurations and the ability to pass customizable SLURM header arguments.

### Full Class Definition

```python
import subprocess
import tempfile

class SLURMDriver:
    def __init__(self):
        self.jobs_registry = {}

    def submit_job(self, container_path, conda_env=None, modules=None, slurm_args=None):
        script_content = self._create_script(container_path, conda_env, modules, slurm_args)
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.sh') as tmpfile:
            tmpfile.write(script_content)
            tmpfile_path = tmpfile.name

        result = subprocess.run(['sbatch', tmpfile_path], capture_output=True, text=True)
        job_id = result.stdout.strip().split()[-1]
        self.jobs_registry[job_id] = {'status': 'submitted', 'script': tmpfile_path}
        return job_id

    def check_job_status(self, job_id):
        if job_id in self.jobs_registry:
            result = subprocess.run(['squeue', '-j', job_id], capture_output=True, text=True)
            if 'PD' in result.stdout:  # Pending
                self.jobs_registry[job_id]['status'] = 'pending'
            elif 'R' in result.stdout:  # Running
                self.jobs_registry[job_id]['status'] = 'running'
            else:
                self.jobs_registry[job_id]['status'] = 'completed or failed'
            return self.jobs_registry[job_id]['status']
        else:
            return 'unknown job id'

    def check_all_job_statuses(self):
        for job_id in self.jobs_registry.keys():
            self.check_job_status(job_id)
        return self.jobs_registry

    def cancel_job(self, job_id):
        if job_id in self.jobs_registry:
            subprocess.run(['scancel', job_id])
            self.jobs_registry[job_id]['status'] = 'cancelled'
            return True
        else:
            return False

    def _create_script(self, container_path, conda_env, modules, slurm_args):
        script_lines = ["#!/bin/bash"]
        if slurm_args:
            for key, value in slurm_args.items():
                script_lines.append(f"#SBATCH --{key}={value}")
        if conda_env:
            script_lines.append(f"source activate {conda_env}")
        if modules:
            for module in modules:
                script_lines.append(f"module load {module}")
        script_lines.append(f"container run {container_path}")
        return "\n".join(script_lines)

```

### Features and Functionalities

- **Dynamic Job Submission**: The `submit_job` method allows for the submission of jobs that involve running containers. It can set up a specific Conda environment and load required modules before executing the container, and it accepts a dictionary of SLURM header arguments for customized job scheduling.
- **Job Status Monitoring**: The `check_job_status` method provides real-time status updates for individual jobs, identifying whether they are pending, running, or have completed.
- **Global Job Status Overview**: `check_all_job_statuses` gives a snapshot of all jobs in the registry, offering a comprehensive view of task distribution and execution status across the cluster.
- **Job Control**: The `cancel_job` method allows for the cancellation of specific jobs, adding a layer of control over the tasks running in the cluster.

### Python Code Example: Utilizing the SLURMDriver

```python
driver = SLURMDriver()
slurm_args = {'cpus-per-task': '4', 'mem': '4G', 'time': '01:00:00'}
job_id = driver.submit_job('/path/to/container', conda_env='my_env', modules=['module1'], slurm_args=slurm_args)
# Simulate a brief wait, then check the status of all jobs
time.sleep(10)
all_jobs_status = driver.check_all_job_statuses()
print(f"All Jobs Status: {all_jobs_status}")
```

In this example, the SLURMDriver submits a job with a container, Conda environment, additional modules, and custom SLURM header arguments. After waiting briefly, the status of all jobs in the cluster is checked, providing a clear overview of each job's current state.

## Conclusion

The SLURMDriver class is a powerful tool for achieving efficiency, control, and transparency in managing distributed computing tasks within scientific environments. It optimizes the utilization of computing resources, ensuring that computational tasks are executed smoothly and effectively in the SLURM environment.
