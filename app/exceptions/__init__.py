class AppError(Exception):
    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(self.message)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed", errors: dict | None = None):
        self.errors = errors or {}
        super().__init__(message)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class AuthorisationError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message)


class BusinessRuleError(AppError):
    def __init__(self, message: str = "Business rule violation", errors: dict | None = None):
        self.errors = errors or {}
        super().__init__(message)


class LockedOutError(AppError):
    def __init__(self, message: str = "Account temporarily locked due to too many failed attempts"):
        super().__init__(message)
