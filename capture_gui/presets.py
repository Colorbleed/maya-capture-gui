import glob
import os
import logging

_registered_paths = []
log = logging.getLogger("Presets")


def discover(paths=None):
    """
    Get the full list of files found in the registered folders
    
    :param paths: list of directories which host preset files
    :type: list
    
    :return: a list of approaved preset file of filetype .JSON
    :rtype: list
    """

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

            # check for file size
            if not check_file_size(filename):
                log.warning("Filesize is smaller than 1 byte "
                               "for file '{}'".format(filename))
                continue

            if filename not in presets:
                presets.append(filename)

    return presets


def check_file_size(filepath):
    """
    Check if filesize of the given file is bigger than 1.0 byte
    
    :param filepath: full filepath of the file to check
    :type filepath: str
    
    :return: 
    """

    file_stats = os.stat(filepath)
    if file_stats.st_size < 1:
        return False
    return True


def preset_paths():
    """
    Get and filter the registered paths
    
    :return: list of filtered registered paths
    :rtype: list
    """

    paths = list()
    for path in _registered_paths:
        if path in paths:
            continue
        paths.append(path)

    return paths


def register_preset_path(path):
    """
    Add filepath to registered presets
    
    :param path: the directory of the preset file(s) 
    :type path: str
    
    :return: 
    """
    if path in _registered_paths:
        return log.warning("Path already registered: {}".format(path))

    _registered_paths.append(path)

    return path


user_folder = os.path.expanduser("~")
capture_gui_presets = os.path.join(user_folder, "CaptureGUI", "presets")
register_preset_path(capture_gui_presets)
