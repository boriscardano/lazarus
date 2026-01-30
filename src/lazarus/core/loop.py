"""Healing loop with retry logic and timing enforcement.

This module provides the HealingLoop class that manages the retry logic for
healing attempts, including attempt counting, timeouts, and loop control.
"""

from __future__ import annotations

import time
from collections.abc import Iterator


class HealingLoop:
    """Manages the healing retry loop with timing and attempt limits.

    This class provides an iterator interface for the healing loop, enforcing
    constraints on maximum attempts and total timeout. It tracks elapsed time
    and provides methods for controlling the loop flow.

    Attributes:
        max_attempts: Maximum number of healing attempts
        timeout_per_attempt: Maximum time for each attempt in seconds
        total_timeout: Maximum total time for all attempts in seconds
        _current_attempt: Current attempt number (0-indexed internally)
        _start_time: Time when the loop started
        _success: Whether healing has succeeded
    """

    def __init__(
        self,
        max_attempts: int = 3,
        timeout_per_attempt: int = 300,
        total_timeout: int = 900,
    ) -> None:
        """Initialize the healing loop.

        Args:
            max_attempts: Maximum number of healing attempts (default: 3)
            timeout_per_attempt: Max time per attempt in seconds (default: 300)
            total_timeout: Max total time for all attempts in seconds (default: 900)

        Raises:
            ValueError: If max_attempts < 1 or timeouts are invalid
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if timeout_per_attempt < 1:
            raise ValueError("timeout_per_attempt must be at least 1")
        if total_timeout < timeout_per_attempt:
            raise ValueError("total_timeout must be >= timeout_per_attempt")

        self.max_attempts = max_attempts
        self.timeout_per_attempt = timeout_per_attempt
        self.total_timeout = total_timeout

        self._current_attempt = 0
        self._start_time: float = 0.0
        self._success = False

    def __iter__(self) -> Iterator[int]:
        """Iterate through healing attempts.

        Yields:
            Attempt number (1-indexed) for each healing attempt

        Example:
            >>> loop = HealingLoop(max_attempts=3, total_timeout=600)
            >>> for attempt_num in loop:
            ...     # Perform healing attempt
            ...     if success:
            ...         loop.mark_success()
            ...         break
        """
        self._start_time = time.time()
        self._current_attempt = 0
        self._success = False

        while self._should_continue():
            self._current_attempt += 1
            yield self._current_attempt

    def _should_continue(self) -> bool:
        """Determine if the loop should continue.

        Returns:
            True if another attempt should be made, False otherwise
        """
        # Check if we've reached max attempts
        if self._current_attempt >= self.max_attempts:
            return False

        # Check if we've exceeded total timeout
        elapsed = time.time() - self._start_time
        if elapsed >= self.total_timeout:
            return False

        # Check if healing succeeded
        if self._success:
            return False

        return True

    def mark_success(self) -> None:
        """Mark the healing as successful.

        This will cause the loop to exit after the current iteration.
        Call this when a healing attempt succeeds.
        """
        self._success = True

    def get_elapsed_time(self) -> float:
        """Get the elapsed time since the loop started.

        Returns:
            Elapsed time in seconds
        """
        if self._start_time == 0.0:
            return 0.0
        return time.time() - self._start_time

    def get_remaining_time(self) -> float:
        """Get the remaining time before total timeout.

        Returns:
            Remaining time in seconds (0 if not started or timeout exceeded)
        """
        if self._start_time == 0.0:
            return 0.0
        elapsed = self.get_elapsed_time()
        remaining = self.total_timeout - elapsed
        return max(0.0, remaining)

    def get_attempts_remaining(self) -> int:
        """Get the number of attempts remaining.

        Returns:
            Number of attempts left (0 if max reached)
        """
        remaining = self.max_attempts - self._current_attempt
        return max(0, remaining)

    def reset(self) -> None:
        """Reset the loop state.

        This allows reusing the same HealingLoop instance for multiple
        healing sessions.
        """
        self._current_attempt = 0
        self._start_time = 0.0
        self._success = False


def create_retry_message(attempt_number: int, max_attempts: int) -> str:
    """Create a user-friendly retry message.

    Args:
        attempt_number: Current attempt number (1-indexed)
        max_attempts: Maximum number of attempts

    Returns:
        Formatted retry message

    Example:
        >>> create_retry_message(2, 3)
        'Retry attempt 2 of 3'
    """
    if attempt_number == 1:
        return f"Initial healing attempt (1 of {max_attempts})"
    else:
        return f"Retry attempt {attempt_number} of {max_attempts}"


def calculate_backoff_delay(attempt_number: int, base_delay: float = 1.0) -> float:
    """Calculate exponential backoff delay for retry attempts.

    This can be used to add delays between retry attempts to give external
    systems time to recover or to avoid rate limiting.

    Args:
        attempt_number: Current attempt number (1-indexed)
        base_delay: Base delay in seconds (default: 1.0)

    Returns:
        Delay in seconds

    Example:
        >>> calculate_backoff_delay(1)
        1.0
        >>> calculate_backoff_delay(2)
        2.0
        >>> calculate_backoff_delay(3)
        4.0
    """
    if attempt_number <= 1:
        return base_delay

    # Exponential backoff: base_delay * 2^(attempt - 1)
    # Capped at 60 seconds
    delay = base_delay * (2 ** (attempt_number - 1))
    return min(delay, 60.0)
