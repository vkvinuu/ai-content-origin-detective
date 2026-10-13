class DetectiveBaseException(Exception):
    """Base exception for all domain errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class SecurityValidationError(DetectiveBaseException):
    """Raised when an uploaded file violates security rules."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class FileProcessingError(DetectiveBaseException):
    """Raised when an image cannot be parsed or processed."""
    def __init__(self, message: str):
        super().__init__(message, status_code=422)

class AnalysisNotFoundError(DetectiveBaseException):
    """Raised when a requested analysis ID does not exist."""
    def __init__(self, analysis_id: str):
        super().__init__(f"Analysis with ID '{analysis_id}' was not found.", status_code=404)

class StorageError(DetectiveBaseException):
    """Raised when an object storage upload/download fails."""
    def __init__(self, message: str):
        super().__init__(f"Storage error: {message}", status_code=502)

class AuthenticationError(DetectiveBaseException):
    """Raised when a token or credentials cannot be validated."""
    def __init__(self, message: str = "Invalid or expired authentication token."):
        super().__init__(message, status_code=401)
