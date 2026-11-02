"""Saturday, July 25, to Sunday, July 26, 2026: the retry storm.

At about 2:14 a.m. CDT on Saturday a partner carrier's notice feed
began answering with its maintenance page, with a status of 200 and
a timestamp in the page, so every fetch had a new digest and the
waiver watch, whose run key is the notice and its digest, saw a new
notice every five minutes. The extraction step sent the page to the
small model; the page was long, the model's answer took longer than
the client's 20-second timeout, and three layers retried:

  model gateway client   3 attempts a call, on timeout or 429
  harness                3 attempts a step
  loop scheduler         a run that timed out re-queued after 5 min,
                         with no cap, because a timeout is "transient"

so every digest became a chain of runs that never ended, nine billed
calls every eight minutes, and the number of chains grew by twelve an
hour. The budget
enforcer reserved once a step and released the reservation when the
client reported no usage, which is what a timed-out call reports, so
the loop's own spend counter read nothing while the provider counted
every call. At Sunday evening's
servicing peak the loop and the servicing agent together passed the
small-model rate limit they share, the servicing agent's calls began
to wait on 429s, and task latency was the first objective to page.

Minute by minute, from fixed parameters (seed 37). The dollars are
Chapter 38's; this module counts calls and tokens. Synthetic;
Lakeshore figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from common.rand import seeded

from .records import Records, Task, Usage, at

START = at("2026-07-25", "02:14")
END = at("2026-07-26", "20:10")
WAKE_EVERY = 5            # minutes, one new digest each
CLIENT, HARNESS = 3, 3    # attempts a call, attempts a step
REQUEUE_AFTER = 5         # minutes; a timeout is "transient", no cap
RUN_MIN = 3               # nine 20-second attempts
LOOP_TOKENS = 1_800       # the maintenance page, truncated, and prompt
SERVICE_TOKENS = 6_217    # Chapter 10's input tokens a model call
LIMIT = 2_000_000         # shared small-model input tokens a minute
# servicing small-model calls a minute, by hour, Saturday and Sunday
SAT = [40, 30, 25, 22, 25, 35, 55, 80, 110, 130, 140, 145, 145, 140,
       135, 130, 135, 145, 160, 165, 150, 120, 90, 60]
SUN = [45, 35, 28, 24, 25, 32, 45, 65, 90, 110, 120, 125, 125, 120,
       120, 125, 140, 140, 170, 245, 230, 190, 130, 80]
CALLS_PER_TASK = 9
RETRY_BACK = 0.9          # share of refused calls some layer resends


@dataclass
class Minute:
    t: object
    chains: int = 0            # digests whose runs keep re-queuing
    loop_billed: int = 0       # loop calls the provider ran and billed
    loop_counted: int = 0      # loop calls the enforcer counted
    loop_limited: int = 0      # loop calls refused 429 (not billed)
    service_calls: int = 0
    service_limited: int = 0

    @property
    def tokens(self) -> int:
        return ((self.service_calls - self.service_limited)
                * SERVICE_TOKENS + self.loop_billed * LOOP_TOKENS)


@dataclass
class Storm:
    minutes: list[Minute] = field(default_factory=list)
    records: Records = field(default_factory=Records)
    digests: int = 0

    def billed(self, until=None) -> int:
        return sum(m.loop_billed for m in self.minutes
                   if until is None or m.t < until)

    def counted(self, until=None) -> int:
        return sum(m.loop_counted for m in self.minutes
                   if until is None or m.t < until)

    def first_limited(self):
        for m in self.minutes:
            if m.service_limited:
                return m.t
        return None

    def at(self, t) -> Minute:
        i = int((t - START).total_seconds() // 60)
        return self.minutes[i]


def simulate(seed: int = 37, stop_at=None, client: int = CLIENT,
             harness: int = HARNESS, requeue: bool = True,
             enforcer_counts_attempts: bool = False) -> Storm:
    """Run the weekend. `stop_at` turns the loop off (tier three);
    `client` and `harness` set the attempts in those layers, and
    `requeue=False` makes the scheduler treat a timeout as a failure
    that goes to a person instead of a run to try again."""
    rng = seeded(seed, "storm")
    st = Storm()
    total = int((END - START).total_seconds() // 60)
    per_run = client * harness
    cycle = per_run / 3 + (REQUEUE_AFTER if requeue else 0)
    carry_svc = carry_loop = 0.0
    for i in range(total):
        t = START + timedelta(minutes=i)
        m = Minute(t)
        if i % WAKE_EVERY == 0:
            st.digests += 1
        stopped = stop_at is not None and t >= stop_at
        if requeue:
            chains = st.digests
            loop = chains * per_run / cycle
        else:
            # each digest runs once, nine calls over three minutes
            chains = 1 if i % WAKE_EVERY < per_run / 3 else 0
            loop = chains * 3.0
        loop = 0.0 if stopped else loop + carry_loop
        sched = SAT if t.day == 25 else SUN
        svc = sched[t.hour] + carry_svc
        want = svc * SERVICE_TOKENS + loop * LOOP_TOKENS
        over = max(0.0, want - LIMIT) / want if want else 0.0
        m.chains = 0 if stopped else chains
        m.service_calls = round(svc)
        m.service_limited = round(svc * over)
        m.loop_limited = round(loop * over)
        m.loop_billed = round(loop) - m.loop_limited
        m.loop_counted = m.loop_billed if enforcer_counts_attempts else 0
        # a refused call comes back: the client retries it, and every
        # layer above that sees the failure retries too
        carry_svc = svc * over * RETRY_BACK
        carry_loop = 0.0 if stopped else loop * over * RETRY_BACK
        st.minutes.append(m)
        st.records.usage.append(Usage(
            t, "agent:waiver-watch", m.loop_billed,
            m.loop_billed * LOOP_TOKENS, m.loop_limited))
        st.records.usage.append(Usage(
            t, "agent:servicing", m.service_calls - m.service_limited,
            (m.service_calls - m.service_limited) * SERVICE_TOKENS,
            m.service_limited))
        _servicing_tasks(st.records, m, sched[t.hour], over, rng)
    return st


def _servicing_tasks(rec: Records, m: Minute, rate: float, over: float,
                     rng) -> None:
    """Servicing tasks ending this minute; a call refused 429 waits
    on the client's backoff (2, 4, 8 s) and retries."""
    n = rng.random() < (rate / CALLS_PER_TASK) % 1
    n = int(rate / CALLS_PER_TASK) + n
    for k in range(n):
        secs = rng.lognormvariate(2.75, 0.42)
        for _ in range(CALLS_PER_TASK):
            back = 2.0
            while rng.random() < over and back <= 8.0:
                secs += back + rng.uniform(0, 1)
                back *= 2
        end = m.t + timedelta(seconds=rng.uniform(0, 59))
        rec.tasks.append(Task(f"S{m.t:%d%H%M}-{k}", "servicing",
                              end - timedelta(seconds=secs), end, True,
                              end))


def hidden_hours(st: Storm, page_at) -> float:
    return (page_at - START).total_seconds() / 3600
