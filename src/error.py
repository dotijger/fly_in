class ParseError(Exception):
    """Shows errors related to a parser issue

    Args:
        BaseException: base exception class.
    """

    def __init__(
        self,
        file: str,
        line_number: str,
        line_content: str,
        message: str,
        expected: str | None = None,
    ) -> None:
        """Creates a parsing error

        Args:
            msg (str): Message to display if the error happens
        """
        self.file = file
        self.line_number = line_number
        self.line_content = line_content
        self.message = message
        self.expected = expected
        super().__init__(str(self))

    def __str__(self) -> str:
        parts = [
            f"ParseError found in {self.file} at line {self.line_number}",
            f"Error: {self.message}",
            "",
            f"Line {self.line_number} | '{self.line_content}'",
        ]
        if self.expected:
            parts += ["", f"Expected: '{self.expected}'"]
        return "\n".join(parts)


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


class SimulationError(Exception):
    """Shows errors related to a simulation issue

    Args:
        BaseException: base exception class.
    """

    def __init__(self, msg: str) -> None:
        """Creates a simulation error

        Args:
            msg (str): Message to display if the error happens
        """
        super().__init__(f"ParseError: {msg}")


class VisualizationError(Exception):
    """Shows errors related to a visualization issue

    Args:
        BaseException: base exception class.
    """

    def __init__(self, msg: str) -> None:
        """Creates a visualization error

        Args:
            msg (str): Message to display if the error happens
        """
        super().__init__(f"VisualizationError: {msg}")
