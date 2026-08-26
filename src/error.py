class ParseError(Exception):
    """Shows errors related to a parser issue

    Args:
        BaseException: base exception class.
    """

    def __init__(self, msg: str) -> None:
        """Creates a logging error

        Args:
            msg (str): Message to display if the error happens
        """
        super().__init__(f"ParseError: {msg}")
