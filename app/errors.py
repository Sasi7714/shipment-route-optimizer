"""Application errors that can be safely returned to API clients."""


class ApplicationError(Exception):
    status_code = 400
    code = "application_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ResourceNotFoundError(ApplicationError):
    status_code = 404
    code = "shipment_not_found"


class FeatureDisabledError(ApplicationError):
    status_code = 503
    code = "feature_disabled"
