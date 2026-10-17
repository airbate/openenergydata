"""Explicit conversion of declared interval energy or power to watts."""
import math


def watts_factor(channel: dict) -> float:
    quantity = channel.get('physical_quantity', 'power')
    unit = channel.get('unit', 'W')
    if quantity == 'normalized' or unit == '1':
        raise ValueError('Normalized dimensionless values cannot be interpreted as physical power; use verified raw readings')
    if quantity == 'energy':
        scale = {'Wh': 1., 'kWh': 1000., 'MWh': 1_000_000.}.get(unit)
        interval = float(channel.get('nominal_interval_s', 0))
        if scale is None or not math.isfinite(interval) or interval <= 0:
            raise ValueError(f'Unsupported energy unit or interval: {unit}, {interval}')
        return scale * 3600. / interval
    if quantity not in ('power', 'active_power', 'apparent_power'):
        raise ValueError(f'Unsupported physical quantity: {quantity}')
    scale = {'W': 1., 'kW': 1000., 'MW': 1_000_000.}.get(unit)
    if scale is None:
        raise ValueError(f'Unsupported power unit: {unit}')
    return scale
