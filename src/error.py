class ParseError(Exception):
    """Shows errors related to a parser issue

    Args:
        BaseException: base exception class.
    """

    def __init__(self, msg: str) -> None:
        """Creates a parsing error

        Args:
            msg (str): Message to display if the error happens
        """
        super().__init__(f"ParseError: {msg}")


class PathError(Exception):
    """Shows errors related to a pathfinder issue

    Args:
        BaseException: base exception class.
    """

    def __init__(self, msg: str) -> None:
        """Creates a pathfinding error

        Args:
            msg (str): Message to display if the error happens
        """
        super().__init__(f"PathError: {msg}")
