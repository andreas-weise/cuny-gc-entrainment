import time
from os import getpid


def is_int(value, name):
    if isinstance(value, int):
        return True
    else:
        raise TypeError('%s must be an integer' % name)


def is_float(value, name):
    if isinstance(value, float):
        return True
    else:
        raise TypeError('%s must be a float' % name)


def is_pos(value, name):
    if value > 0:
        return True
    else:
        raise ValueError('%s must have positive value' % name)


def is_in_list(value, val_list, name):
    if value in val_list:
        return True
    else:
        raise ValueError('%s must be in %s' % (name, val_list))


def is_less_or_equal(left_val, right_val, left_name, right_name):
    if left_val <= right_val:
        return True
    else:
        raise ValueError('%s must be less than or equal to %s' %
                         (left_name, right_name))


def get_unique_fname(name, ftype=None):
    """makes a file name more unique by adding a process id and timestamp to it

    args:
        name: file name including path, excluding file type
        ftype: file type including '.'
    """
    return '%s_%s_%d%s' % (name, time.strftime('%Y%m%d%H%M%S'), getpid(), ftype)
