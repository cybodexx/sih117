from __future__ import annotations


class AegisError(Exception):
    """Base error for the AEGIS system. Maps to RFC 9457 problem+json."""

    code: str = "internal_error"
    status: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class NotFound(AegisError):
    code = "not_found"
    status = 404
    detail = "The requested resource was not found."


class Forbidden(AegisError):
    code = "forbidden"
    status = 403
    detail = "You do not have permission to access this resource."


class ClearanceDenied(Forbidden):
    code = "clearance_denied"
    detail = "Insufficient clearance level."


class DepartmentDenied(Forbidden):
    code = "department_denied"
    detail = "You do not have access to this department's resources."


class Unauthorized(AegisError):
    code = "unauthorized"
    status = 401
    detail = "Authentication required."


class BadRequest(AegisError):
    code = "bad_request"
    status = 400
    detail = "Invalid request."


class Conflict(AegisError):
    code = "conflict"
    status = 409
    detail = "Resource already exists."


class IngestError(AegisError):
    code = "ingest_failed"
    status = 422
    detail = "Document ingestion failed."


class UnsupportedModality(IngestError):
    code = "unsupported_modality"
    detail = "The file type is not supported."


class ModelUnavailable(AegisError):
    code = "model_unavailable"
    status = 503
    detail = "The local model runtime did not respond."


class BudgetExceeded(AegisError):
    code = "budget_exceeded"
    status = 429
    detail = "Agent budget exceeded."


class ToolError(AegisError):
    code = "tool_error"
    status = 422
    detail = "A tool call failed."


class SovereigntyBreach(AegisError):
    code = "sovereignty_breach"
    status = 500
    detail = "An outbound network connection was detected."
