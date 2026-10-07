"""Doubly constrained entropy OD inference. Costs are network travel seconds.

Only net redistribution is identifiable: this is a minimum-movement estimate,
not an observed trip matrix. Local/outsider labels are location-relative and
must not be fitted as if they were conserved traveler identities.
"""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class FitReport:
    production: float
    attraction: float
    residual: float
    attraction_scale: float
    iterations: int
    max_marginal_error: float


def estimate_od(deltas, costs, beta=1 / 1800, tolerance=1e-7,
                max_iterations=10000, balance="normalize", prior=None):
    """Return dense T, audit report. Unreachable pairs have cost +inf.

    Row/column order matches deltas. Destination masses are scaled to origins
    under normalize; strict rejects drift. One-sided changes cannot be inferred.
    A strictly positive pair prior can encode functional attraction without
    relaxing the marginals. Solver works in log space to avoid decay underflow.
    """
    d = np.asarray(deltas, dtype=float)
    c = np.asarray(costs, dtype=float)
    if d.ndim != 1 or c.shape != (len(d), len(d)):
        raise ValueError("Expected deltas [n] and costs [n,n]")
    if not np.isfinite(d).all() or np.isnan(c).any() or (c < 0).any():
        raise ValueError("Deltas must be finite; costs must be nonnegative or +inf")
    if not np.isfinite(beta) or beta < 0 or tolerance <= 0 or max_iterations < 1:
        raise ValueError("Invalid solver parameters")
    if balance not in ("normalize", "strict"):
        raise ValueError("balance must be normalize or strict")
    oi, dj = np.where(d < 0)[0], np.where(d > 0)[0]
    o, a = -d[oi], d[dj]
    production, attraction = float(o.sum()), float(a.sum())
    report = FitReport(production, attraction, attraction-production, 1, 0, 0)
    result = np.zeros_like(c)
    if production == attraction == 0:
        return result, asdict(report)
    if min(production, attraction) == 0:
        raise ValueError("One-sided population change: needs explicit external source/sink")
    if balance == "strict" and abs(production-attraction) > tolerance * max(1, production):
        raise ValueError("Unbalanced population: strict conservation failed")
    report.attraction_scale = production / attraction
    a = a * report.attraction_scale
    subset = c[np.ix_(oi, dj)]
    log_kernel = -beta * np.where(np.isfinite(subset), subset, 0)
    # beta=0 still preserves structural zeros.
    log_kernel[~np.isfinite(c[np.ix_(oi, dj)])] = -np.inf
    if prior is not None:
        p = np.asarray(prior, dtype=float)
        if p.shape != c.shape or not np.isfinite(p).all() or (p <= 0).any():
            raise ValueError("Pair prior must be finite, positive and [n,n]")
        log_kernel += np.log(p[np.ix_(oi, dj)])
    if (~np.isfinite(log_kernel).any(axis=1)).any() or (~np.isfinite(log_kernel).any(axis=0)).any():
        raise ValueError("Unreachable origin or destination: no street route; no straight-line fallback")

    def logsumexp(x, axis):
        m = np.max(x, axis=axis, keepdims=True)
        return (m + np.log(np.sum(np.exp(x-m), axis=axis, keepdims=True))).squeeze(axis)

    log_o, log_a = np.log(o), np.log(a)
    v = np.zeros(len(a))
    for iteration in range(1, max_iterations+1):
        u = log_o-logsumexp(log_kernel+v[None, :], 1)
        v = log_a-logsumexp(log_kernel+u[:, None], 0)
        if iteration % 5 == 0 or iteration == max_iterations:
            t = np.exp(log_kernel+u[:, None]+v[None, :])
            error = max(float(np.max(np.abs(t.sum(axis=1)-o))),
                        float(np.max(np.abs(t.sum(axis=0)-a))))
            if error <= tolerance * max(1, production):
                result[np.ix_(oi, dj)] = t
                report.iterations, report.max_marginal_error = iteration, error
                return result, asdict(report)
    raise ValueError("Furness did not converge: disconnected/infeasible support or iteration limit")
