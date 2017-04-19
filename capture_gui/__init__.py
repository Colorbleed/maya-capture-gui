

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

    parent = lib.get_maya_main_window()
    window = app.App(title="Capture GUI",
                     objectname="CaptureGui",
                     parent=parent)

    if show:
        window.show()

    return window
