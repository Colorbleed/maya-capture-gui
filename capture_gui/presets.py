import glob
import os
import math
import logging


_registered_paths = []
logger = logging.getLogger("Presets")


def discover(paths=None):

    presets = []
    for path in paths or preset_paths():
        path = os.path.normpath(path)
        if not os.path.isdir(path):
            continue

        # check for json files
        glob_query = os.path.abspath(os.path.join(path, "*.json"))
        filenames = glob.glob(glob_query)
        for filename in filenames:
            # skip private files
            if filename.startswith("_"):
                continue

            # check for filesize
            if not check_file_size(filename):
                logger.warning("Filesize is smaller than 1 byte "
                               "for file '{}'".format(filename))
                continue

            if filename not in presets:
                presets.append(filename)

    return presets


def check_file_size(filepath):
    """
    Check if filesize of the given file is bigger than 1.0 byte
    :param filepath: 
    :return: 
    """

    file_stats = os.stat(filepath)
    filesize = math.floor(file_stats.st_size)
    if filesize < 1.0:
        return False
    return True


def preset_paths():

    paths = list()
    for path in _registered_paths:
        if path in paths:
            continue
        paths.append(path)

    return paths


def register_preset_path(path):
    if path in _registered_paths:
        return logger.warning("Path already registered: {0}".format(path))

    _registered_paths.append(path)

    return path



user_folder = os.path.expanduser("~")
capture_gui_presets = os.path.join(user_folder, "CaptureGUI", "presets")
print capture_gui_presets
register_preset_path(capture_gui_presets)

