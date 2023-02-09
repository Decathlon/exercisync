

class DecathlonAuthorizationMappingError(Exception):
    def __init__(self, authorization_dict, message) -> None:
        self.authorization_dict = authorization_dict
        self.message = message
        super().__init__(message)