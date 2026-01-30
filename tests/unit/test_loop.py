"""Tests for the HealingLoop class."""

import time

import pytest

from lazarus.core.loop import (
    HealingLoop,
    calculate_backoff_delay,
    create_retry_message,
)


def test_healing_loop_initialization():
    """Test that HealingLoop initializes correctly."""
    loop = HealingLoop(max_attempts=3, timeout_per_attempt=100, total_timeout=300)

    assert loop.max_attempts == 3
    assert loop.timeout_per_attempt == 100
    assert loop.total_timeout == 300


def test_healing_loop_invalid_max_attempts():
    """Test that HealingLoop raises ValueError for invalid max_attempts."""
    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        HealingLoop(max_attempts=0)


def test_healing_loop_invalid_timeout():
    """Test that HealingLoop raises ValueError for invalid timeouts."""
    with pytest.raises(ValueError, match="timeout_per_attempt must be at least 1"):
        HealingLoop(max_attempts=3, timeout_per_attempt=0)

    with pytest.raises(ValueError, match="total_timeout must be >= timeout_per_attempt"):
        HealingLoop(max_attempts=3, timeout_per_attempt=300, total_timeout=100)


def test_healing_loop_iteration():
    """Test that HealingLoop iterates correctly."""
    loop = HealingLoop(max_attempts=3, timeout_per_attempt=10, total_timeout=30)

    attempts = []
    for attempt_num in loop:
        attempts.append(attempt_num)
        if attempt_num == 2:
            loop.mark_success()
            break

    assert attempts == [1, 2]


def test_healing_loop_max_attempts():
    """Test that HealingLoop respects max_attempts."""
    loop = HealingLoop(max_attempts=3, timeout_per_attempt=10, total_timeout=100)

    attempts = []
    for attempt_num in loop:
        attempts.append(attempt_num)

    assert attempts == [1, 2, 3]


def test_healing_loop_mark_success():
    """Test that mark_success stops the loop."""
    loop = HealingLoop(max_attempts=5, timeout_per_attempt=10, total_timeout=100)

    attempts = []
    for attempt_num in loop:
        attempts.append(attempt_num)
        if attempt_num == 2:
            loop.mark_success()

    assert attempts == [1, 2]


def test_healing_loop_elapsed_time():
    """Test that get_elapsed_time works correctly."""
    loop = HealingLoop(max_attempts=3, timeout_per_attempt=10, total_timeout=30)

    # Before starting
    assert loop.get_elapsed_time() == 0.0

    # Start the loop
    for attempt_num in loop:
        time.sleep(0.1)
        elapsed = loop.get_elapsed_time()
        assert elapsed > 0.0
        break


def test_healing_loop_remaining_time():
    """Test that get_remaining_time works correctly."""
    loop = HealingLoop(max_attempts=3, timeout_per_attempt=10, total_timeout=30)

    # Before starting
    assert loop.get_remaining_time() == 0.0

    # Start the loop
    for attempt_num in loop:
        time.sleep(0.1)
        remaining = loop.get_remaining_time()
        assert 0.0 < remaining <= 30.0
        break


def test_healing_loop_attempts_remaining():
    """Test that get_attempts_remaining works correctly."""
    loop = HealingLoop(max_attempts=3, timeout_per_attempt=10, total_timeout=30)

    attempts_seen = []
    for attempt_num in loop:
        attempts_seen.append(attempt_num)
        remaining = loop.get_attempts_remaining()

        if attempt_num == 1:
            assert remaining == 2
        elif attempt_num == 2:
            assert remaining == 1
        elif attempt_num == 3:
            assert remaining == 0


def test_healing_loop_reset():
    """Test that reset() clears loop state."""
    loop = HealingLoop(max_attempts=3, timeout_per_attempt=10, total_timeout=30)

    # Run once
    for attempt_num in loop:
        if attempt_num == 2:
            loop.mark_success()
            break

    # Reset
    loop.reset()

    # Run again
    attempts = []
    for attempt_num in loop:
        attempts.append(attempt_num)
        if attempt_num == 1:
            break

    assert attempts == [1]


def test_create_retry_message():
    """Test retry message creation."""
    msg1 = create_retry_message(1, 3)
    assert "Initial healing attempt" in msg1
    assert "1 of 3" in msg1

    msg2 = create_retry_message(2, 3)
    assert "Retry attempt 2 of 3" in msg2

    msg3 = create_retry_message(3, 5)
    assert "Retry attempt 3 of 5" in msg3


def test_calculate_backoff_delay():
    """Test exponential backoff calculation."""
    # First attempt: base delay
    assert calculate_backoff_delay(1) == 1.0

    # Second attempt: 2x base delay
    assert calculate_backoff_delay(2) == 2.0

    # Third attempt: 4x base delay
    assert calculate_backoff_delay(3) == 4.0

    # Fourth attempt: 8x base delay
    assert calculate_backoff_delay(4) == 8.0

    # Should cap at 60 seconds
    assert calculate_backoff_delay(10) == 60.0

    # Custom base delay
    assert calculate_backoff_delay(1, base_delay=2.0) == 2.0
    assert calculate_backoff_delay(2, base_delay=2.0) == 4.0
