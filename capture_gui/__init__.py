

def main(show=True):
    """Convenience method to run the Application inside Maya.

    Args:
        show (bool): Whether to directly show the instantiated application.
            Defaults to True. Set this to False if you want to manage the
            application (like callbacks) prior to showing the interface.

    Returns:
        capture_gui.app.App: The pyblish gui application instance.

    """
    from . import app
    from . import lib

    # get main maya window to parent widget to
    parent = lib.get_maya_main_window()

    # kill any running instance of the app to ensure callbacks are correct
    lib.ensure_single_instance(app.App)

    # launch app
    window = app.App(title="Capture GUI",
                     objectname="CaptureGui",
                     parent=parent)

    if show:
        window.show()

    return window
