import sys
import logging
import json
import os
import glob
import subprocess
import contextlib

import datetime
import maya.cmds as cmds
import maya.mel as mel
import capture

from .vendor.Qt import QtWidgets

log = logging.getLogger(__name__)


OBJECT_TYPES = {'Cameras': 'cameras',
                'Control Vertices': 'controlVertices',
                'Deformers': 'deformers',
                'Dimensions': 'dimensions',
                'Dynamic Constraints': 'dynamicConstraints',
                'Dynamics': 'dynamics',
                'Fluids': 'fluids',
                'Follicles': 'follicles',
                'Grid': 'grid',
                'Hair Systems': 'hairSystems',
                'Handles': 'handles',
                'Hulls': 'hulls',
                'Ik Handles': 'ikHandles',
                'ImagePlane': 'imagePlane',
                'Joints': 'joints',
                'Lights': 'lights',
                'Locators': 'locators',
                'Manipulators': 'manipulators',
                'nCloths': 'nCloths',
                'nParticles': 'nParticles',
                'nRigids': 'nRigids',
                'NURBS Curves': 'nurbsCurves',
                'NURBS Surfaces': 'nurbsSurfaces',
                'Pivots': 'pivots',
                'Planes': 'planes',
                'Polygons': 'polymeshes',
                'Strokes': 'strokes',
                'Subdiv Surfaces': 'subdivSurfaces',
                'Textures': 'textures'}


def get_current_scenename():
    path = cmds.file(query=True, sceneName=True)
    if path:
        return os.path.splitext(os.path.basename(path))[0]
    return None


def get_current_camera():
    """Returns the currently active camera.

    Searched in the order of:
        1. Active Panel
        2. Selected Camera Shape
        3. Selected Camera Transform

    Returns:
        str: name of active camera transform

    """

    # Get camera from active modelPanel  (if any)
    panel = cmds.getPanel(withFocus=True)
    if cmds.getPanel(typeOf=panel) == "modelPanel":
        cam = cmds.modelEditor(panel, query=True, camera=True)
        # In some cases above returns the shape, but most often it returns the
        # transform. Still we need to make sure we return the transform.
        if cam:
            if cmds.nodeType(cam) == "transform":
                return cam
            # camera shape is a shape type
            elif cmds.objectType(cam, isAType="shape"):
                parent = cmds.listRelatives(cam, parent=True, fullPath=True)
                if parent:
                    return parent[0]

    # Check if a camShape is selected (if so use that)
    cam_shapes = cmds.ls(selection=True, type="camera")
    if cam_shapes:
        return cmds.listRelatives(cam_shapes,
                                  parent=True,
                                  fullPath=True)[0]

    # Check if a transform of a camShape is selected
    # (return cam transform if any)
    transforms = cmds.ls(selection=True, type="transform")
    if transforms:
        cam_shapes = cmds.listRelatives(transforms, shapes=True, type="camera")
        if cam_shapes:
            return cmds.listRelatives(cam_shapes,
                                      parent=True,
                                      fullPath=True)[0]


def get_active_editor():
    """Return the active editor panel to playblast with"""
    # fixes `cmds.playblast` undo bug
    cmds.currentTime(cmds.currentTime(query=True))
    panel = cmds.playblast(activeEditor=True)
    return panel.split("|")[-1]


def get_current_frame():
    return cmds.currentTime(query=True)


def get_time_slider_range(highlighted=True,
                          withinHighlighted=True,
                          highlightedOnly=False):
    """Return the time range from Maya's time slider.

    Arguments:
        highlighted (bool): When True if will return a selected frame range
            (if there's any selection of more than one frame!) otherwise it
            will return min and max playback time.
        withinHighlighted (bool): By default Maya returns the highlighted range
            end as a plus one value. When this is True this will be fixed by
            removing one from the last number.

    Returns:
        list: List of two floats of start and end frame numbers.

    """
    if highlighted is True:
        gPlaybackSlider = mel.eval("global string $gPlayBackSlider; "
                                   "$gPlayBackSlider = $gPlayBackSlider;")
        if cmds.timeControl(gPlaybackSlider, query=True, rangeVisible=True):
            highlightedRange = cmds.timeControl(gPlaybackSlider,
                                                query=True,
                                                rangeArray=True)
            if withinHighlighted:
                highlightedRange[-1] -= 1
            return highlightedRange
    if not highlightedOnly:
        return [cmds.playbackOptions(query=True, minTime=True),
                cmds.playbackOptions(query=True, maxTime=True)]


def get_current_renderlayer():
    return cmds.editRenderLayerGlobals(query=True, currentRenderLayer=True)


def get_plugin_shapes():
    """
    Get all currently available plugin shapes
    :return: dictionary
    """
    filters = cmds.pluginDisplayFilter(query=True, listFilters=True)
    labels = [cmds.pluginDisplayFilter(f, query=True, label=True) for f in
              filters]
    return dict(zip(labels, filters))


def open_file(filepath):
    """Open file using OS default settings"""
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', filepath))
    elif os.name == 'nt':
        os.startfile(filepath)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', filepath))
    else:
        raise NotImplementedError("OS not supported: {0}".format(os.name))


def load_json(filepath):
    """open and read json, return read values"""
    with open(filepath, "r") as f:
        return json.load(f)


def _fix_playblast_output_path(filepath):
    """Workaround a bug in maya.cmds.playblast to return correct filepath.

    When the `viewer` argument is set to False and maya.cmds.playblast does not
    automatically open the playblasted file the returned filepath does not have
    the file's extension added correctly.

    To workaround this we just glob.glob() for any file extensions and assume
    the latest modified file is the correct file and return it.

    """
    # Catch cancelled playblast
    if filepath is None:
        log.warning("Playblast did not result in output path. "
                    "Playblast is probably interrupted.")
        return

    # Fix: playblast not returning correct filename (with extension)
    # Lets assume the most recently modified file is the correct one.
    if not os.path.exists(filepath):
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        # check if the filepath is has frame based filename
        # example : capture.####.png
        parts = filename.split(".")
        if len(parts) == 3:
            query = os.path.join(directory, "{}.*.{}".format(parts[0],
                                                             parts[-1]))
            files = glob.glob(query)
        else:
            files = glob.glob("{}.*".format(filepath))

        if not files:
            raise RuntimeError("Couldn't find playblast from: "
                               "{0}".format(filepath))
        filepath = max(files, key=os.path.getmtime)

    return filepath


def capture_scene(options):
    """Capture using scene settings.

    Uses the view settings from "panel".

    This ensures playblast is done as quicktime H.264 100% quality.
    It forces showOrnaments to be off and does not render off screen.

    Arguments:
        high_quality (bool): If true the playblast will be forced to
            use Viewport 2.0 and enable Anti-aliasing.

    Returns:
        str: Full path to playblast file.

    """

    filename = options.get("filename", "%TEMP%")
    log.info("Capturing to: {0}".format(filename))

    options = options.copy()

    # Force viewer to False in call to capture because we have our own
    # viewer opening call to allow a signal to trigger between playblast
    # and viewer
    options['viewer'] = False

    # Remove panel key since it's internal value to capture_gui
    options.pop("panel", None)

    print options["display_options"]

    path = capture.capture(**options)
    path = _fix_playblast_output_path(path)

    return path


def browse(path=None):
    """Open a pop-up browser for the user"""

    # Acquire path from user input if none defined
    if path is None:

        scene_path = cmds.file(query=True, sceneName=True)

        # use scene file name as default name
        default_filename = os.path.splitext(os.path.basename(scene_path))[0]
        if not default_filename:
            # Scene wasn't saved yet so found no valid name for playblast.
            default_filename = "playblast"

        # Default to images rule (if rule exists in workspace)
        images_rule = cmds.workspace(variableEntry="images")
        if images_rule:
            root = cmds.workspace(query=True, rootDirectory=True)
            default_root = os.path.join(root, images_rule)
        else:
            # start browser at last browsed directory
            default_root = cmds.workspace(query=True, directory=True)

        # This should never be the case, but just to be safe.
        if default_root is None:
            raise RuntimeError("defaultRoot couldn't be defined. "
                               "Contact your local Technical Director!")

        default_path = os.path.join(default_root, default_filename)
        path = cmds.fileDialog2(fileMode=0,
                                dialogStyle=2,
                                startingDirectory=default_path)

    if not path:
        return

    if isinstance(path, (tuple, list)):
        path = path[0]

    if path.endswith(".*"):
        path = path[:-2]

    # Bug-Fix/Workaround:
    # Fix for playblasts that result in nesting of the
    # extension (eg. '.mov.mov.mov') which happens if the format
    # is defined in the filename used for saving.
    extension = os.path.splitext(path)[-1]
    if extension:
        path = path[:-len(extension)]

    return path


def default_output():
    """Generate outpath based on current scenename and set project"""

    workspace = cmds.workspace(query=True, rootDirectory=True)
    folder = cmds.workspace(fileRuleEntry="images")
    scene = get_current_scenename() or "playblast"

    # get current datetime
    timestamp = datetime.datetime.today()
    str_timestamp = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
    filename = "{}_{}".format(scene, str_timestamp)

    return os.path.join(workspace, folder, filename)


def list_formats():
    # Workaround for Maya playblast bug where undo would
    # move the currentTime to frame one.
    cmds.currentTime(cmds.currentTime(query=True))
    return cmds.playblast(query=True, format=True)


def list_compressions(format='avi'):
    # Workaround for Maya playblast bug where undo would
    # move the currentTime to frame one.
    cmds.currentTime(cmds.currentTime(query=True))

    cmd = 'playblast -format "{0}" -query -compression'.format(format)
    return mel.eval(cmd)


@contextlib.contextmanager
def no_undo():
    """Disable undo during the context"""
    try:
        cmds.undoInfo(stateWithoutFlush=False)
        yield
    finally:
        cmds.undoInfo(stateWithoutFlush=True)


def get_maya_main_window():
    """Return Maya's main window"""
    for obj in QtWidgets.QApplication.topLevelWidgets():
        if obj.objectName() == 'MayaWindow':
            return obj
