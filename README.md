# Clock Skew Detector

Estimates the offset between a local clock and a remote clock from round-trip probes that carry remote-observed timestamps.

```python
from clock_skew_detector import SkewEstimator, estimate_offset

est = SkewEstimator()
est.add_probe(local_send_ms=1000.0, remote_recv_ms=1500.0, remote_send_ms=1510.0)
est.add_probe(local_send_ms=2000.0, remote_recv_ms=2500.0, remote_send_ms=2510.0)
result = est.estimate()
print(result.offset_ms, result.n)

# or statelessly:
result = estimate_offset([(1000.0, 1500.0, 1510.0), (2000.0, 2500.0, 2510.0)])
```

## Why this exists

When a remote service echoes its own timestamps (HTTP `Date` headers, NTP-style payloads, log lines), you can recover how far its clock is from yours without an out-of-band protocol. The estimator takes the midpoint of each probe's `(remote_recv, remote_send)` window and subtracts the local send time. Under symmetric path latency, the one-way delays cancel in the median, so the estimate converges to the true offset even when the one-way delays themselves are unknown.

The deliberate trade-off: robustness over precision. We report the median offset, which tolerates up to half the probes being corrupted by queueing spikes or retransmits but will not improve in precision as you add clean probes beyond the median's natural resolution. If you need sub-millisecond accuracy you want a proper NTP or PTP client, not this library.

## Edge cases you will hit

- Fewer than two probes yield `n == 0` and `offset_ms == 0.0`. The first probe is always discarded because its RTT typically includes first-hop DNS/TLS work that does not recur, and a single remaining probe carries no robustness signal.
- The estimator does not see `local_recv`; it cannot compute true RTT. `rtt_ms` is reported as `0.0` and is reserved for a future richer probe format. Do not rely on it.
- Timestamps must be in milliseconds in any consistent epoch (POSIX epoch, boot-relative, TAI). Mixing epochs across probes produces garbage.

## Exported names

- `SkewEstimator` — class. Methods: `add_probe(local_send_ms, remote_recv_ms, remote_send_ms)`, `estimate() -> SkewEstimate`.
- `SkewEstimate` — frozen dataclass with fields `offset_ms`, `rtt_ms`, `n`.
- `estimate_offset(probes)` — functional shortcut taking an iterable of `(local_send_ms, remote_recv_ms, remote_send_ms)` triples.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

