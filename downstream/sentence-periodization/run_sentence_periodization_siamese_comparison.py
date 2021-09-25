

import os
import collections
import tqdm
import numpy as np
import pandas as pd
from kneed import KneeLocator


def classify(scores, background_y):
    knees = []
    gt = np.cumsum(scores[:, np.argsort(background_y)], axis=1)
    for row in tqdm.tqdm(np.arange(len(scores))):
        knee = KneeLocator(
            np.sort(background_y), gt[row], 
            curve='concave', interp_method='polynomial'
        ).knee
        knee = knee if knee is not None else np.nan
        knees.append(knee)
    return np.array(knees)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model1-eval') # './bert-periodization-scores-span=25.npz'
    parser.add_argument('--model2-eval') # './macberth-periodization-scores-span=25.npz'
    parser.add_argument('--background',
        default='./data/sentence-periodization/periodization.background.csv')
    parser.add_argument('--output-prefix', default='./data/sentence-periodization')
    parser.add_argument('--output-path', required=True)
    args = parser.parse_args()

    if not os.path.isdir(args.output_prefix):
        os.makedirs(args.output_prefix)


    data1 = np.load(args.model1_eval)
    scores1, background_y, dev_y_orig = data1['scores'], data1['background_y'], data1['dev_y_orig']
    data2 = np.load(args.model2_eval)
    scores2 = data2['scores']
    background = pd.read_csv(args.background)
    span = 50
    background['span'] = span * (background['year'] // span)

    data = collections.defaultdict(list)
    for n_per_bin in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        for iteration in range(10):
            sample = background.groupby('span').sample(n_per_bin, replace=False)
            knees1 = classify(scores1[:, sample.index], background_y[sample.index])
            knees2 = classify(scores2[:, sample.index], background_y[sample.index])
            nans1, = np.where(np.isnan(knees1))
            nans2, = np.where(np.isnan(knees2))
            nans = np.union1d(nans1, nans2)
            mask = np.ones(len(knees1))
            mask[nans] = 0
            mask = mask.astype(np.bool)
            data['iteration'].append(iteration)
            data['n_per_bin'].append(n_per_bin)
            data['n_backgrouund'].append(len(sample))
            data['n_items'].append(len(mask[mask]))
            data['mae-model1'].append(np.nanmean(np.abs(knees1[mask] - dev_y_orig[mask])))
            data['mae-model2'].append(np.nanmean(np.abs(knees2[mask] - dev_y_orig[mask])))

    pd.DataFrame.from_dict(data).to_csv(os.path.join(args.output_prefix, args.output_path))