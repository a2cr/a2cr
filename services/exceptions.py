class AppError(Exception):
    def __init__(self, code: str, message: str, status: int):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)


class SlotLimitExceeded(AppError):
    def __init__(self):
        super().__init__("slot_limit_exceeded", "Maximum slot count (3) reached", 400)


class ContentTooLarge(AppError):
    def __init__(self):
        super().__init__("content_too_large", "Content exceeds 10KB limit", 400)


class InvalidSlotName(AppError):
    def __init__(self):
        super().__init__("invalid_slot_name", "slot_name must match ^[a-zA-Z0-9_-]{1,64}$", 400)


class SlotNotFound(AppError):
    def __init__(self):
        super().__init__("slot_not_found", "Slot not found or expired", 404)
