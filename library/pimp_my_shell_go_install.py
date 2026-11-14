#!/usr/bin/python
"""Install one Go tool with a deadline that owns the entire build process group."""

import os
import signal
import subprocess

from ansible.module_utils.basic import AnsibleModule


DOCUMENTATION = r"""
---
module: pimp_my_shell_go_install
short_description: Install a Go tool with process-group timeout cleanup
description:
  - Runs go install without a shell and kills the build process group on timeout.
  - Uses the task environment for Go installation and host architecture settings.
options:
  package:
    description: Go package and version to install.
    type: str
    required: true
  jobs:
    description: Maximum parallel Go build jobs.
    type: int
    required: true
  timeout:
    description: Maximum seconds allowed for the build.
    type: int
    required: true
  chdir:
    description: Working directory for the build.
    type: path
    required: true
author:
  - Phil (@mr-pmillz)
"""

EXAMPLES = r"""
- name: Install iferr
  pimp_my_shell_go_install:
    package: github.com/koron/iferr@latest
    jobs: 2
    timeout: 900
    chdir: /home/user
"""

RETURN = r"""
rc:
  description: Build exit status, or 124 when the deadline expires.
  type: int
  returned: always
stdout:
  description: Captured build output.
  type: str
  returned: always
stderr:
  description: Captured compiler or download diagnostics.
  type: str
  returned: always
"""


def run_build(command, directory, timeout):
    # setsid runs in the child BEFORE exec. Assigning its group in the parent
    # after fork races with early compiler children (as Ansible async can do).
    with subprocess.Popen(
        command, cwd=directory, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8", errors="replace", start_new_session=True,
    ) as process:
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        return {
            "rc": 124 if timed_out else process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": timed_out,
        }


def main():
    module = AnsibleModule(argument_spec={
        "package": {"type": "str", "required": True},
        "jobs": {"type": "int", "required": True},
        "timeout": {"type": "int", "required": True},
        "chdir": {"type": "path", "required": True},
    })
    params = module.params
    if params["jobs"] <= 0 or params["timeout"] <= 0:
        module.fail_json(msg="jobs and timeout must be positive integers")
    command = [module.get_bin_path("go", required=True), "install", "-v",
               "-p", str(params["jobs"]), params["package"]]
    try:
        result = run_build(command, params["chdir"], params["timeout"])
    except OSError as error:
        module.fail_json(msg=str(error), changed=False, cmd=command)
    result.update(changed=True, cmd=command)
    if result.pop("timed_out"):
        module.fail_json(
            msg=f"Timeout exceeded after {params['timeout']}s installing {params['package']}; "
                "terminated the build process group", **result,
        )
    if result["rc"] != 0:
        module.fail_json(msg=f"go install failed for {params['package']}", **result)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
