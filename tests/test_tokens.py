from services.tokens import count_tokens, original_tokens_from_length
import math


def test_count_tokens_returns_positive_int():
    result = count_tokens('{"goal": "test", "current_state": "ok", "next_action": "go"}')
    assert isinstance(result, int)
    assert result > 0


def test_count_tokens_empty_string():
    result = count_tokens("")
    assert result == 0


def test_original_tokens_from_length_divides_by_3():
    assert original_tokens_from_length(3000) == 1000
    assert original_tokens_from_length(3001) == 1001  # ceil
    assert original_tokens_from_length(3) == 1


def test_original_tokens_from_length_zero():
    assert original_tokens_from_length(0) == 0


def test_original_tokens_from_none_returns_none():
    from services.tokens import original_tokens_from_length_optional
    assert original_tokens_from_length_optional(None) is None
    assert original_tokens_from_length_optional(6000) == 2000
