"""A28 distribution declarations; no arbitrary code execution or global RNG state."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

NORMAL = NormalDist()
KINDS = {
    'constant': {'value'}, 'normal': {'mean', 'std'},
    'truncated_normal': {'mean', 'std', 'low', 'high'},
    'lognormal': {'mean', 'log_sd', 'std'}, 'uniform': {'low', 'high'},
    'choice': {'values', 'weights'}, 'values': {'values'},
}


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return value


def log_spread(spec):
    if 'log_sd' in spec:
        return spec['log_sd']
    if spec['mean'] == 0:
        if spec['std'] != 0:
            raise ValueError('zero lognormal mean requires zero std')
        return 0.
    try:
        spread = math.sqrt(math.log1p((spec['std'] / spec['mean']) ** 2))
    except OverflowError as error:
        raise ValueError('lognormal std/mean ratio is too large') from error
    if not math.isfinite(spread):
        raise ValueError('lognormal std/mean ratio is too large')
    return spread


def validate_distribution(spec, *, low=None, high=None, strict_low=False, size=None):
    if not isinstance(spec, dict) or spec.get('kind') not in KINDS:
        raise ValueError(f'distribution kind must be one of {sorted(KINDS)}')
    kind = spec['kind']
    keys = set(spec) - {'kind'}
    required = KINDS[kind] - ({'weights'} if kind == 'choice' else set())
    if kind == 'lognormal':
        required = {'mean'}
        if len(keys & {'std', 'log_sd'}) != 1:
            raise ValueError('lognormal requires exactly one of std or log_sd')
    if not required <= keys or keys - KINDS[kind]:
        raise ValueError(f'{kind}: required fields {sorted(required)}; unknown {sorted(keys - KINDS[kind])}')
    if kind in {'values', 'choice'}:
        values = spec['values']
        if not isinstance(values, list) or not values:
            raise ValueError('values must be a nonempty list')
        for v in values:
            number(v, 'distribution value')
        if kind == 'values' and size is not None and len(values) != size:
            raise ValueError(f'exact values need {size} entries, got {len(values)}')
        support = min(values), max(values)
        if kind == 'choice' and 'weights' in spec:
            weights = spec['weights']
            if not isinstance(weights, list) or len(weights) != len(values):
                raise ValueError('choice weights must match values')
            for v in weights:
                if number(v, 'choice weight') < 0:
                    raise ValueError('choice weights must be nonnegative')
            if not math.isfinite(sum(weights)) or sum(weights) <= 0:
                raise ValueError('choice weights must have positive finite total')
    else:
        for key in keys:
            number(spec[key], key)
        if kind == 'constant':
            support = spec['value'], spec['value']
        elif kind in {'normal', 'truncated_normal'}:
            if spec['std'] < 0:
                raise ValueError('std must be nonnegative')
            if kind == 'normal':
                support = ((spec['mean'], spec['mean']) if spec['std'] == 0 else (-math.inf, math.inf))
            else:
                if spec['low'] >= spec['high']:
                    raise ValueError('truncation requires low < high')
                if spec['std'] == 0 and not spec['low'] <= spec['mean'] <= spec['high']:
                    raise ValueError('zero-spread mean must lie within truncation bounds')
                if spec['std'] > 0:
                    lo = NORMAL.cdf((spec['low'] - spec['mean']) / spec['std'])
                    hi = NORMAL.cdf((spec['high'] - spec['mean']) / spec['std'])
                    if hi <= lo:
                        raise ValueError('truncation interval has no representable probability mass')
                support = ((spec['mean'], spec['mean']) if spec['std'] == 0 else (spec['low'], spec['high']))
        elif kind == 'lognormal':
            if spec['mean'] < 0 or spec.get('log_sd', spec.get('std')) < 0:
                raise ValueError('lognormal mean and spread must be nonnegative')
            sigma = log_spread(spec)
            support = ((spec['mean'], spec['mean']) if sigma == 0 or spec['mean'] == 0
                       else (0, math.inf))
        else:
            if spec['low'] > spec['high']:
                raise ValueError('uniform requires low <= high')
            support = spec['low'], spec['high']
    a, b = support
    # A lognormal with positive mean has open lower support: every realized value is positive.
    open_zero = kind == 'lognormal' and spec['mean'] > 0
    if low is not None and (a < low or (strict_low and a == low and not (low == 0 and open_zero))):
        raise ValueError(f'distribution support must be {">" if strict_low else ">="} {low}')
    if high is not None and b > high:
        raise ValueError(f'distribution support must be <= {high}')


def sample_distribution(spec, z, *, low=None, high=None, strict_low=False):
    """Map fixed standard-normal draws into a declared distribution (paired quantiles)."""
    z = np.asarray(z, dtype=float)
    validate_distribution(spec, low=low, high=high, strict_low=strict_low, size=z.size)
    kind = spec['kind']
    if kind == 'constant':
        out = np.full(z.shape, spec['value'], dtype=float)
    elif kind == 'values':
        out = np.asarray(spec['values'], dtype=float).reshape(z.shape)
    elif kind == 'lognormal':
        sigma = log_spread(spec)
        with np.errstate(over='ignore', under='ignore'):
            out = spec['mean'] * np.exp(sigma * z - .5 * sigma ** 2)
    elif kind in {'normal', 'truncated_normal'} and spec['std'] == 0:
        out = np.full(z.shape, spec['mean'], dtype=float)
    elif kind == 'normal':
        out = spec['mean'] + spec['std'] * z
    else:
        u = np.array([NORMAL.cdf(float(v)) for v in z.flat]).reshape(z.shape)
        if kind == 'uniform':
            out = spec['low'] + (spec['high'] - spec['low']) * u
        elif kind == 'choice':
            weights = np.asarray(spec.get('weights', [1] * len(spec['values'])), dtype=float)
            cumulative = np.cumsum(weights / weights.sum())
            ix = np.minimum(np.searchsorted(cumulative, u, side='right'), len(weights) - 1)
            out = np.asarray(spec['values'], dtype=float)[ix]
        else:
            lo = NORMAL.cdf((spec['low'] - spec['mean']) / spec['std'])
            hi = NORMAL.cdf((spec['high'] - spec['mean']) / spec['std'])
            q = np.clip(lo + u * (hi - lo), np.nextafter(0., 1.), np.nextafter(1., 0.))
            out = np.array([spec['mean'] + spec['std'] * NORMAL.inv_cdf(float(v)) for v in q.flat]).reshape(z.shape)
            # Roundoff only: declared support already passed validation.
            out = np.clip(out, spec['low'], spec['high'])
    if not np.all(np.isfinite(out)):
        raise ValueError('distribution produced nonfinite samples; reduce its spread')
    if low is not None and np.any(out <= low if strict_low else out < low):
        raise ValueError('sample violates lower state bound')
    if high is not None and np.any(out > high):
        raise ValueError('sample violates upper state bound')
    return out
