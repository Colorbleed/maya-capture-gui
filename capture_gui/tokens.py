"""Token system

The capture gui application will format tokens in the filename.
The tokens can be registered using `register_token`

"""
from . import lib

_registered_tokens = dict()


def format_tokens(string, options):
    """
    Replace the tokens with the correlated strings

    :param string: the filename of the playblast
    :type string: str

    :param options: the capture options
    :type options: dict

    :return: the formatted filename with all tokens resolved
    :rtype: str
    """

    if not string:
        return string

    for token, value in _registered_tokens.items():
        if token in string:
            func = value['func']
            string = string.replace(token, func(options))

    return string


def register_token(token, func, label=""):
    assert token.startswith("<") and token.endswith(">")
    assert callable(func)
    _registered_tokens[token] = {"func": func, "label": label}


def list_tokens():
    return _registered_tokens.copy()


# register default tokens
# scene based tokens
register_token("<Camera>",
               lambda options: options['camera'].rsplit("|", 1)[-1],
               label="Insert camera name")
register_token("<Scene>", lambda options: lib.get_current_scenename() or "playblast",
               label="Insert current scene name")
register_token("<RenderLayer>", lambda options: lib.get_current_renderlayer(),
               label="Insert active render layer name")

# project based tokens
register_token("<Images>",
               lambda options: lib.get_project_rule("images"),
               label="Insert image directory of set project")
register_token("<Movies>",
               lambda options: lib.get_project_rule("movie"),
               label="Insert movies directory of set project")
