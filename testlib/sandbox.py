from typing import List, Optional


def get_sandbox_command(has_internet: bool, blacklist_dirs: List[str], real_command: List[str] or str,
                        available_binaries: List[str], return_list: bool, cgroups: Optional[List[str]] = None,
                        user: Optional[str] = None):
    command = 'firejail --private-dev --shell=none --seccomp --quiet --caps --noroot'
    blacklist_dirs = blacklist_dirs.copy()
    if user:
        command = 'sudo -u ' + user + ' ' + command
    else:
        command += ' --private'
    if not has_internet:
        command += ' --net=none'
    blacklist_dirs.append('/sys/fs/cgroup')
    for i in blacklist_dirs:
        command += f' --blacklist={i}'
    if available_binaries:
        command += f' --private-bin=' + ','.join(available_binaries)
    if cgroups:
        for cgroup in cgroups:
            command += f' --cgroup=/sys/fs/cgroup/{cgroup}/tasks'
    command += ' env -i LC_ALL=en_US.UTF-8 PATH=/bin:/usr/bin:/usr/local/bin '
    if isinstance(real_command, list):
        command += ' '.join(real_command)
    else:
        command += real_command
    if return_list:
        return command.split(' ')
    return command
