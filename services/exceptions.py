class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        extra: dict | None = None,
        headers: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra or {}
        self.headers = headers or {}
        super().__init__(message)


class SlotLimitExceeded(AppError):
    def __init__(self):
        super().__init__("slot_limit_exceeded", "Maximum slot count (3) reached", 400)


class InvalidSlotNumber(AppError):
    def __init__(self):
        super().__init__("invalid_slot_number", "slot_number must be between 1 and 3", 400)


class SlotNameConflict(AppError):
    def __init__(self):
        super().__init__("slot_name_conflict", "slot_name already belongs to another slot", 409)


class ContentTooLarge(AppError):
    def __init__(self):
        super().__init__("content_too_large", "Content exceeds 10KB limit", 400)


class InvalidSlotName(AppError):
    def __init__(self):
        super().__init__("invalid_slot_name", "slot_name must match ^[a-zA-Z0-9_-]{1,64}$", 400)


class SlotNotFound(AppError):
    def __init__(self):
        super().__init__("slot_not_found", "Slot not found or expired", 404)


class RetentionNotAllowed(AppError):
    def __init__(self):
        super().__init__("retention_not_allowed", "Retention is not allowed for this plan", 422)


class DetailLevelNotAllowed(AppError):
    def __init__(self):
        super().__init__("detail_level_not_allowed", "Detail level is not allowed for this plan", 422)


class BodyTooLarge(AppError):
    def __init__(self):
        super().__init__("body_too_large", "Request body exceeds this plan's limit", 413)


class PlanLimitExceeded(AppError):
    def __init__(self, code: str, message: str, retry_after: int = 3600):
        super().__init__(
            code,
            message,
            429,
            extra={"retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )
