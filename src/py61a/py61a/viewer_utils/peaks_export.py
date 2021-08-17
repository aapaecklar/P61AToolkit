import pandas as pd
import numpy as np
from typing import Union
from functools import reduce
import random
import string


def read_peaks(f_names: Union[str, list, tuple] = ()) -> pd.DataFrame:
    """
    Reads P61A::Viewer output files and combines them together.
    :param f_names: file path(s): a string or a tuple / list of strings
    :return: data as a pandas DataFrame
    """
    fake_prefixes = ('eh1', 'exp', 'xspress3')  # some motor names start with these + underscore

    def get_prefix(col_name: str) -> tuple:
        parts = col_name.split('_')
        if len(parts) == 1 or parts[0] in fake_prefixes:
            return 'md', col_name
        else:
            return parts[0], '_'.join(parts[1:])

    if isinstance(f_names, str):
        f_names = [f_names]

    if len(f_names) == 0:
        return pd.DataFrame()

    data = []
    for f_name in f_names:
        data.append(pd.read_csv(f_name, index_col=0))
        data[-1].columns = pd.MultiIndex.from_tuples([get_prefix(col) for col in data[-1].columns],
                                                     names=['prefix', 'parameter'])
    data = reduce(merge_peak_datasets, data)

    for peak in valid_peaks(data, valid_for='phase'):
        for k in ('h', 'k', 'l'):
            data.loc[:, (peak, k)] = data[peak][k].mean(skipna=True)
        phase = data[peak]['phase']
        phase = phase[~phase.isna()]
        data.loc[:, (peak, 'phase')] = phase.iloc[0]
    return data


def merge_peak_datasets(d1, d2):
    """
    :param d1:
    :param d2:
    :return:
    """
    def hkl_match(d1_, col1_, d2_, col2_):
        if ('h' not in d1_[col1_].columns) or \
           ('k' not in d1_[col1_].columns) or \
           ('l' not in d1_[col1_].columns) or \
           ('h' not in d2_[col2_].columns) or \
           ('k' not in d2_[col2_].columns) or \
           ('l' not in d2_[col2_].columns):
            return False
        else:
            return (d1_[col1_]['h'].mean().astype(np.int) == d2_[col2_]['h'].mean().astype(np.int)) and \
                   (d1_[col1_]['k'].mean().astype(np.int) == d2_[col2_]['k'].mean().astype(np.int)) and \
                   (d1_[col1_]['l'].mean().astype(np.int) == d2_[col2_]['l'].mean().astype(np.int))

    def next_prefix(px_, pxs_):
        i, idx = -1, 0
        while i > -len(px_):
            try:
                idx = int(px_[i:])
            except ValueError:
                i += 1
                break
            i -= 1

        while True:
            idx += 1
            if (px_[:i] + str(idx)) not in pxs_:
                return px_[:i] + str(idx)

    known_prefixes = set(d2.columns.get_level_values(0))
    known_prefixes.update(set(d1.columns.get_level_values(0)))
    known_prefixes.remove('md')
    d2_lvl0_mapping = dict()

    for col2 in set(d2.columns.get_level_values(0)):
        if col2 == 'md':
            continue

        match = False

        for col1 in set(d1.columns.get_level_values(0)):
            if hkl_match(d1, col1, d2, col2):
                match = True
                break

        if match:
            d2_lvl0_mapping[col2] = col1
        else:
            if col2 in d1.columns.get_level_values(0):
                d2_lvl0_mapping[col2] = next_prefix(col2, known_prefixes)
                known_prefixes.add(d2_lvl0_mapping[col2])

    d2_lvl0_mapping['md'] = 'md'
    d2 = d2.rename(columns=d2_lvl0_mapping)
    d1.sort_index(inplace=True, axis=1)
    d2.sort_index(inplace=True, axis=1)
    d2.index = d2.index + d1.shape[0]

    return pd.concat((d1, d2), axis=0)


def valid_peaks(data: pd.DataFrame, valid_for: Union[str, None] = 'sin2psi'):
    """

    :param data:
    :param valid_for: sin2psi,
    :return:
    """
    columns_sin2psi = (
        'h', 'k', 'l', 'phase',
        'center', 'center_std',
    )

    columns_hkl = (
        'h', 'k', 'l', 'phase',
    )

    prefixes = set(data.columns.get_level_values(0))

    try:
        prefixes.remove('md')
    except KeyError:
        pass

    if valid_for in ('sin2psi', 'phase'):
        if valid_for == 'sin2psi':
            nc = columns_sin2psi
        elif valid_for == 'phase':
            nc = columns_hkl

        invalid = set()

        for prefix in prefixes:
            if not all(x in data[prefix].columns for x in nc):
                invalid.update({prefix})

        for prefix in invalid:
            prefixes.remove(prefix)
    else:
        pass
    return list(prefixes)


def peak_id_str(data: pd.DataFrame, peak_id: str) -> str:
    try:
        return '%s [%d%d%d]' % (data[peak_id]['phase'].iloc[0],
                                *tuple(data[peak_id][['h', 'k', 'l']].mean().astype(int).tolist()))
    except Exception:
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
