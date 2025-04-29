class MissingIDError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class LegislationParsingError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class IvalidCitationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
