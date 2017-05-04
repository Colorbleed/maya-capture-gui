### Playblasting in Maya done with GUI

A visual interface for
[maya-capture](https://github.com/abstractfactory/maya-capture).

<img align="right" src="https://cloud.githubusercontent.com/assets/2439881/18627536/c1a6b4e4-7e5b-11e6-9c69-047bd5cbbce5.jpg"/>

> WARNING: Preview release

<br>

### Features

- Set up your playblasts visually (with direct feedback). 
- Produce consistent predictable playblasts.
- Callbacks to allow custom encoding prior to opening viewer.
- Avoid unwanted overscan; playblast what you render.

<br>

### Installation

To install, download this package and [capture](https://github.com/abstractfactory/maya-capture)
and place both in a directory where Maya can find them.

<br>

### Usage

To show the interface in Maya run:

```python
import capture_gui
capture_gui.main()
```

<br>

### Advanced

#### Callbacks
Register a pre-view callback to allow a custom conversion or overlays on the 
resulting footage in your pipeline (e.g. through FFMPEG)

```python
import capture_gui

# Use Qt.py to be both compatible with PySide and PySide2 (Maya 2017+)
from capture_gui.vendor.Qt import QtCore

def callback(options):
    """Implement your callback here"""

    print("Callback before launching viewer..")

    # Debug print all options for example purposes
    import pprint
    pprint.pprint(options)

    filename = options['filename']
    print("Finished callback for video {0}".format(filename))


app = capture_gui.main(show=False)

# Use QtCore.Qt.DirectConnection to ensure the viewer waits to launch until
# your callback has finished. This is especially important when using your
# callback to perform an extra encoding pass over the resulting file.
app.viewer_start.connect(callback, QtCore.Qt.DirectConnection)

# Show the app manually
app.show()
```

#### Register preset paths

Register a preset path that will be used by the capture gui to load default presets from.

```python
import capture_gui.presets
import capture_gui

path = "path/to/directory"
capture_gui.presets.register_path(path)

# After registering capture gui will automatically load
# the presets found in all registered preset paths
capture_gui.main()
```

#### Register tokens and translators

Register a token and translator that will be used to translate any tokens
in the given filename.

```python
import capture.tokens
import capture_gui

# this is an example function which retrieves the name of the current user
def get_user_name():
    import getpass
    return getpass.getuser()

# register the token <User> and pass the function which should be called
# when this token is present.
# The label is for the right mouse button menu's readability.
capture.tokens.register_token("<User>",
                              lambda options : get_user_name(),
                              label="Insert current user's name")
```

### Known issues

##### Viewport Plugin _show_ menu close button sometimes appears off screen when torn off

Tearing off the _show_ menu in the Viewport Plugin results in a menu
with an off screen title bar when torn off near the top edge of the
screen. This makes it hard to close the menu. To fix this either close
the capture GUI (to close the menu) or make a new torn off version of
the _show_ menu at a lower position on screen (this will close the
previous torn off menu).
