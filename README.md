### Playblasting in Maya done with GUI

A visual interface front-end for
[maya-capture](https://github.com/abstractfactory/maya-capture).

![Capture GUI preview](https://cloud.githubusercontent.com/assets/2439881/18618526/d90fd9bc-7de8-11e6-83a3-ed02ff513c7d.png)

_Currently this is a initial commit to open discussion about overall
implementation.  
As such, consider this experimental and not fit for production
yet._

### Usage

Take control over your Maya playblast. Become the boss over the settings like
resolutions, nodes to show and anything related to the view. While managing
your settings instantly see what your playblast will look like, WYSIWYG.

For `capture_gui` to work you'll need to have `capture` installed, which you
can get [here](https://github.com/abstractfactory/maya-capture).

To show the interface in Maya run:

```python
import capture_gui.app
from capture_gui.vendor.Qt import QtWidgets


def get_maya_main_window():
    """Return Maya's main window"""
    for obj in QtWidgets.qApp.topLevelWidgets():
        if obj.objectName() == 'MayaWindow':\
            return obj


maya_window = get_maya_main_window()
app = capture_gui.app.App(parent=maya_window)
app.show()
```

#### Advanced usages

Register a pre-view callback to allow a custom conversion of the resulting
footage in your pipeline (e.g. through FFMPEG)

```python
import capture_gui.app
from capture_gui.vendor.Qt import QtWidgets


def get_maya_main_window():
    """Return Maya's main window"""
    for obj in QtWidgets.qApp.topLevelWidgets():
        if obj.objectName() == 'MayaWindow':\
            return obj


def callback(options):
    """Implement your callback here"""

    print("Callback before launching viewer..")

    # Debug print all options for example purposes
    import pprint
    pprint.pprint(options)

    filename = options['filename']
    print("Finished callback for video {0}".format(filename))


maya_window = get_maya_main_window()
app = capture_gui.app.App(parent=maya_window)

# Use QtCore.Qt.DirectConnection to ensure the viewer waits to launch until
# your callback has finished. This is especially important when using your
# callback to perform an extra encoding pass over the resulting file.
app.viewer_start.connect(callback, QtCore.Qt.DirectConnection)

app.show()
```