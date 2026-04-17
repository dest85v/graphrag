# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""List of exception names to skip for retries."""

_default_exceptions_to_skip = [
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "UnprocessableEntityError",
    "APIConnectionError",
    "APIError",
    "APIResponseValidationError",
    "InternalServerError",
    "RateLimitError",
    "APITimeoutError",
    "ConflictError",
]
