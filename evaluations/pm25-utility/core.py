"""Pure preparation/statistics for the frozen retrospective PM2.5 evaluation."""
from __future__ import annotations
import hashlib
import numpy as np
import pandas as pd

FEATURES = ['pm25_now', 'pm25_previous', 'pm10_now', 'wind_now']
HEADERS = FEATURES + ['target']
ANCHOR = pd.Timestamp('2016-01-01')


def prepare(raw: pd.DataFrame, station: str, start: str, end: str):
    """Join neighboring timestamps before applying complete-case eligibility."""
    if set(raw['station'].dropna().astype(str)) != {station}:
        raise ValueError('Unexpected or mixed station identity')
    dates = pd.to_datetime(raw[['year', 'month', 'day', 'hour']], errors='raise')
    if dates.duplicated().any():
        raise ValueError('Duplicate timestamps in station file')
    source = raw.copy()
    source.index = pd.DatetimeIndex(dates)
    source = source.sort_index()
    for name in ['PM2.5', 'PM10', 'WSPM']:
        source[name] = pd.to_numeric(source[name], errors='coerce')
    # The scheduled denominator includes absent origin timestamps as well as NA rows.
    origins = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq='h')
    origins = origins[origins.hour % 6 == 0]
    frame = pd.DataFrame(index=origins)
    frame['pm25_now'] = source['PM2.5'].reindex(origins).to_numpy()
    frame['pm25_previous'] = source['PM2.5'].reindex(origins-pd.Timedelta(hours=1)).to_numpy()
    frame['pm10_now'] = source['PM10'].reindex(origins).to_numpy()
    frame['wind_now'] = source['WSPM'].reindex(origins).to_numpy()
    frame['target'] = source['PM2.5'].reindex(origins+pd.Timedelta(hours=1)).to_numpy()
    matrix = frame[HEADERS].to_numpy(dtype=float)
    finite = np.isfinite(matrix).all(axis=1)
    in_range = ((matrix >= 0) & (matrix <= 1e6)).all(axis=1)
    eligible = finite & in_range
    meta = {'station': station, 'scheduled': len(origins), 'eligible': int(eligible.sum()),
            'excluded': int((~eligible).sum()), 'nonfinite_or_missing': int((~finite).sum()),
            'finite_out_of_range': int((finite & ~in_range).sum()),
            'coverage': float(eligible.mean()), 'start': str(origins.min()), 'end': str(origins.max())}
    return frame.loc[eligible].copy(), meta


def select_development(frame: pd.DataFrame) -> pd.DataFrame:
    unique = frame.sort_index().drop_duplicates(subset=FEATURES, keep='first')
    if len(unique) < 2000:
        raise ValueError('Fewer than 2,000 eligible distinct-input development rows')
    ranked = sorted(unique.index, key=lambda t: hashlib.sha256(
        ('pm25-utility-v1|' + t.strftime('%Y-%m-%dT%H:%M:%S')).encode('ascii')).hexdigest())
    return unique.loc[ranked[:2000]].sort_index()


def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict:
    actual, predicted = np.asarray(actual, float), np.asarray(predicted, float)
    if actual.shape != predicted.shape or actual.ndim != 1 or not len(actual):
        raise ValueError('Invalid prediction dimensions')
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError('Nonfinite prediction or target; do not silently drop rows')
    residual = predicted - actual
    variance = np.var(actual)
    mse = float(np.mean(residual**2))
    return {'n': len(actual), 'mse': mse, 'rmse': float(np.sqrt(mse)),
            'mae': float(np.mean(np.abs(residual))),
            'r2': float(1-mse/variance) if variance > 0 else None}


def clip_predictions(values: np.ndarray):
    values = np.asarray(values, float)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite prediction on an eligible row')
    return np.maximum(values, 0), int((values < 0).sum())


def bootstrap_ratio(cohorts: list[dict], replicates: int = 4000) -> dict:
    """Resample aligned calendar weeks jointly for all sites and both models."""
    sums = np.zeros((len(cohorts), 53, 3), dtype=float)
    for site, cohort in enumerate(cohorts):
        times = pd.DatetimeIndex(cohort['times'])
        blocks = np.asarray((times-ANCHOR).total_seconds() // (7*86400), dtype=int)
        if np.any((blocks < 0) | (blocks >= 53)):
            raise ValueError('Test timestamps outside frozen 2016 blocks')
        actual = np.asarray(cohort['actual'], float)
        tool = np.asarray(cohort['tool'], float)
        baseline = np.asarray(cohort['baseline'], float)
        metrics(actual, tool); metrics(actual, baseline)
        np.add.at(sums[site,:,0], blocks, (tool-actual)**2)
        np.add.at(sums[site,:,1], blocks, (baseline-actual)**2)
        np.add.at(sums[site,:,2], blocks, 1)
        if (sums[site,:,2] > 0).sum() < 26:
            raise ValueError('Insufficient populated seven-day blocks')
    total = sums.sum(axis=1)
    denom = np.mean(total[:,1]/total[:,2])
    if denom <= 0:
        raise ValueError('Zero-error baseline: relative advantage is undefined')
    observed = float(np.sqrt(np.mean(total[:,0]/total[:,2])/denom))
    rng = np.random.default_rng(20260915)
    estimates = []
    for _ in range(replicates):
        block_ids = rng.integers(0, 53, size=53)
        boot = sums[:,block_ids,:].sum(axis=1)
        if np.any(boot[:,2] == 0) or np.mean(boot[:,1]/boot[:,2]) <= 0:
            raise ValueError('Degenerate bootstrap replicate')
        estimates.append(float(np.sqrt(np.mean(boot[:,0]/boot[:,2]) / np.mean(boot[:,1]/boot[:,2]))))
    return {'ratio': observed, 'ci95': np.quantile(estimates,[.025,.975]).tolist(),
            'replicates': replicates, 'seed': 20260915, 'block_days': 7,
            'calendar_blocks': 53, 'nonempty_blocks_by_site': (sums[:,:,2]>0).sum(axis=1).tolist(),
            'joint_resampling_across_sites': True}


def advantage_gate(comparisons: list[dict], ratio_ci_upper: float) -> bool:
    return bool(ratio_ci_upper < 1 and all(
        c['tool_rmse'] <= .95*c['baseline_rmse'] and
        c['tool_rmse'] <= .95*c['persistence_rmse'] and
        c['tool_mae'] <= 1.05*c['baseline_mae'] and
        c['tool_mae'] <= 1.05*c['persistence_mae']
        for c in comparisons))
