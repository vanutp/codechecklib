import errno
import os
import random
import string


def mkdtemp(dir):
    for seq in range(os.TMP_MAX):
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        file = os.path.join(dir, 'tmp' + name)
        try:
            os.mkdir(file)
        except FileExistsError:
            continue  # try again
        return file

    raise FileExistsError(errno.EEXIST, 'No usable temporary directory name found')
