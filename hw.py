import psutil
import platform


def get_readable_size(bytes, suffix="B"):
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor


def get_system_info():
    """
    Get system information

    Returns dictionary:
        `op_system (string)`: Operating System 
        `sys_name (string)`: System name
    """

    uname = platform.uname()

    return {
        "op_system": uname.system,
        "sys_name": uname.node,
    }
