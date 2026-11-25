"""Open a task directory without following symlinks, then run the pinned supervisor."""
import os
import pathlib
import re
import resource
import sys

identity = sys.argv[1]
resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024 * 1024, 128 * 1024 * 1024))
if identity == "@recover":
    os.chdir("/var/tmp")
else:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", identity):
        sys.exit(1)
    root = os.open("/data/workspaces", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            os.mkdir(identity, mode=0o700, dir_fd=root)
        except FileExistsError:
            pass
        task = os.open(identity, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
        try:
            os.fchdir(task)
        finally:
            os.close(task)
    finally:
        os.close(root)
program = pathlib.Path("/opt/nod-workspace-programs/command.py").read_text()
exec(compile(program, "/opt/nod-workspace-programs/command.py", "exec"))
