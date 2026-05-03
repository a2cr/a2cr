import math
from typing import Optional
import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in text using cl100k_base encoding."""
    return len(_encoding.encode(text))


def original_tokens_from_length(char_count: int) -> int:
    """Convert character count to estimated token count (ceil(n/3), Japanese-safe)."""
    return math.ceil(char_count / 3)


def original_tokens_from_length_optional(char_count: Optional[int]) -> Optional[int]:
    """Return None if char_count is None, otherwise convert."""
    if char_count is None:
        return None
    return original_tokens_from_length(char_count)
