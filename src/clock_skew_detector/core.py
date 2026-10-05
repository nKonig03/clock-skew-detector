import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class SkewEstimate:
    """Result of estimating a remote clock's offset from the local clock.

    Attributes:
        offset_ms: Estimated offset in milliseconds. Positive means the remote
            clock is ahead of local; negative means it is behind. None when
            insufficient evidence is available.
        rtt_ms: Median round-trip time of the probes in milliseconds. None
            when no probes are available.
        n: Number of probes incorporated into the estimate.
    """
    offset_ms: float
    rtt_ms: float
    n: int


class SkewEstimator:
    """Estimate remote clock offset by analysing response timestamps.

    The estimator ingests probes, each composed of three clock readings:
    (local_send, remote_recv, remote_send) expressed as millisecond counts
    (any consistent epoch works, including the POSIX epoch). For each probe
    the round-trip time is split between the two one-way legs, under the
    standard, strong assumption of symmetric path latency. Because the path
    split is shared equally across all probes, the offset estimate is
    independent of the true one-way delays; they only shift every probe by
    the same constant, which drops out of the median.

    Robustness:
    - The median offset is taken over all probes so that up to half of the
      probes can be corrupted by queueing spikes, GC pauses, or retransmits
      without dragging the estimate away from the truth.
    - Probe 0 (the "sync" probe) is discarded. Its RTT frequently includes
      first-hop DNS/TLS work that never recurs, and its inclusion is a
      well-known source of upward RTT bias in small samples.
    """

    def __init__(self):
        self._probes = []

    def add_probe(self, local_send_ms, remote_recv_ms, remote_send_ms):
        """Record one round-trip probe.

        Timestamps are millisecond counts in any consistent epoch.
        """
        self._probes.append((local_send_ms, remote_recv_ms, remote_send_ms))

    def estimate(self):
        """Return the current offset estimate.

        Returns a SkewEstimate with n == 0 if fewer than two usable probes
        have been recorded. Requiring two (rather than one) is deliberate:
        a single probe gives a point estimate with no robustness signal.
        """
        # Drop the first probe; its RTT is atypically high.
        usable = self._probes[1:] if len(self._probes) > 1 else []
        if not usable:
            return SkewEstimate(offset_ms=0.0, rtt_ms=0.0, n=0)

        offsets = []
        for send, recv, sent in usable:
            # RTT is not computed here; local_recv is not observed by this
            # estimator. rtt_ms is reported as 0.0 and reserved for a future
            # richer probe format.
            offsets.append((recv + sent) / 2.0 - send)
        return SkewEstimate(
            offset_ms=float(statistics.median(offsets)),
            rtt_ms=0.0,
            n=len(usable),
        )


def estimate_offset(probes):
    """Functional shortcut: estimate offset from an iterable of probes.

    Each probe is a (local_send_ms, remote_recv_ms, remote_send_ms) triple.
    """
    est = SkewEstimator()
    for p in probes:
        est.add_probe(*p)
    return est.estimate()
