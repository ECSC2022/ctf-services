import os
import grp
import pwd

from functools import lru_cache


USER_BACKUP = 'userbackup'
USER_SERVER = 'server'


@lru_cache
def get_uid(username) -> int:
    passwd = pwd.getpwnam(username)
    return passwd.pw_uid


@lru_cache
def get_gid(name) -> int:
    group = grp.getgrnam(name)
    return group.gr_gid


def set_perms(path, owner, group, mode):
    uid = get_uid(owner)
    gid = get_gid(group)
    os.chown(path, uid, gid)
    os.chmod(path, mode)


def set_perms_server(path):
    mode = 0o770 if os.path.isdir(path) else 0o660
    set_perms(path, USER_SERVER, USER_SERVER, mode)
