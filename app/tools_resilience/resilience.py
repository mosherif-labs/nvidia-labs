import functools, json, os, random, time
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)


class TransientToolError(Exception): ...


class CircuitOpenError(Exception): ...


DEAD_LETTERS: list[
    dict
] = []  # this process's dead letters: the agent reads it to escalate


def chaos(fn, rate=float(os.environ.get("CHAOS_RATE", "0"))):
    @functools.wraps(fn)
    def wrapped(*a, **kw):
        if random.random() < rate:
            raise TransientToolError(f"{fn.__name__}: injected 503")
        return fn(*a, **kw)

    return wrapped


class CircuitBreaker:
    def __init__(self, fail_max=5, reset_after=30.0):
        self.fail_max, self.reset_after = fail_max, reset_after
        self.failures, self.opened_at = 0, None

    def call(self, fn, *a, **kw):
        if (
            self.opened_at is not None
            and time.monotonic() - self.opened_at < self.reset_after
        ):
            raise CircuitOpenError("circuit open: failing fast")  # OPEN
        try:  # CLOSED, or HALF-OPEN trial
            result = fn(*a, **kw)
        except Exception:
            self.failures += 1
            if self.opened_at is not None or self.failures >= self.fail_max:
                self.opened_at = time.monotonic()  # trip (or re-trip)
            raise
        self.failures, self.opened_at = 0, None  # success closes it
        return result


def resilient(fn, breaker: CircuitBreaker, dead_letters="dead_letters.jsonl"):
    @retry(
        retry=retry_if_exception_type((TransientToolError, TimeoutError)),
        wait=wait_random_exponential(multiplier=0.5, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def attempt(*a, **kw):
        return breaker.call(fn, *a, **kw)

    @functools.wraps(fn)
    def call(*a, **kw):
        try:
            return attempt(*a, **kw)
        except Exception as e:  # exhausted, open, or permanent
            letter = {"tool": fn.__name__, "args": kw, "error": repr(e)}
            DEAD_LETTERS.append(letter)
            with open(dead_letters, "a") as f:
                f.write(json.dumps(letter) + "\n")
            return f"ERROR: {fn.__name__} unavailable ({type(e).__name__}). Try another tool or report partial findings."

    return call
