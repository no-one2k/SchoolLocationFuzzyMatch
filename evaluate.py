from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import StratifiedShuffleSplit
from termcolor import cprint
import argparse
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from classifier.classifier import pipeline
from confusion import plot_confusion_matrix
from utils import current_git_sha


def compare(eval_a_fn, eval_b_fn):
    """We're happy if eval_b is better than eval_a
    """

    eval_a, eval_b = None, None

    with open(eval_a_fn) as f:
        eval_a = json.load(f)

    with open(eval_b_fn) as f:
        eval_b = json.load(f)

    b_f1 = eval_b['weighted_f1_score']
    a_f1 = eval_a['weighted_f1_score']

    print("{: <24}  {: <22}   {: <22}   {: <22}".format('Comparing', eval_a_fn, eval_b_fn, 'diff'))
    print_comparison("Weighted F1 Scores", a_f1, b_f1)

    for metric in eval_a['class_f1_scores'].keys():
        print_comparison(metric,
                         eval_a['class_f1_scores'][metric],
                         eval_b['class_f1_scores'][metric])


def print_comparison(name, a, b):
    diff = b - a
    if diff > 0:
        color = 'green'
    elif diff == 0:
        color = 'white'
    else:
        color = 'red'

    cprint("{: <24}: {:.22f} {:.22f} {:.22f}".format(name, a, b, diff), color)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Evaluate the school classification model.')
    parser.add_argument('-t', '--train',
                        action='store',
                        default='data/ccd_sch_029_1617_w_Oe_050317.csv',
                        dest='train_file',
                        help='Dataset to train on')
    parser.add_argument('-e', '--test',
                        action='store',
                        dest='test_file',
                        help='Dataset to test on. If not set, a split of'
                             ' TRAIN_FILE will be used')
    parser.add_argument('-c', '--confusion-matrix',
                        action='store_const',
                        const=True,
                        default=False,
                        dest='confusion_matrix',
                        help='Compute a confusion matrix')
    args = parser.parse_args()

    np.random.seed(0)

    data = pd.read_csv(args.train_file, encoding='iso-8859-1')
    X = data.drop(['Class'], axis=1)
    y = data['Class']
    unique_labels = y.unique()

    if args.test_file:
        pass
        train_X, train_y = X, y
        test_data = pd.read_csv(args.test_file, encoding='iso-8859-1')
        test_X = test_data.drop(['Class'], axis=1)
        test_y = test_data['Class']
    else:
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.33)
        # Take first split pair generated by splitter. If we were doing
        # multiple train/test splits, this would be invalid, but we'd need a
        # way to aggregate the scores for multiple splits.
        split = next(splitter.split(X, y))
        (train_idx, test_idx) = split
        train_X, train_y = X.iloc[train_idx], y[train_idx]
        test_X, test_y = X.iloc[test_idx], y[test_idx]

    pipeline.fit(train_X, train_y)
    y_true = test_y
    y_pred = pipeline.predict(test_X)

    weighted_f1_score = f1_score(y_true, y_pred, average='weighted')
    f1_scores = f1_score(y_true, y_pred,
                         average=None,
                         labels=unique_labels)
    class_f1_scores = dict(zip(unique_labels, f1_scores))

    evaluation = {
        'weighted_f1_score': weighted_f1_score,
        'class_f1_scores': class_f1_scores
    }

    filename = 'evaluation-{}.json'.format(current_git_sha())
    with open(filename, 'w') as f:
        json.dump(evaluation, f,
                  sort_keys=True,
                  indent=4,
                  separators=(',', ': '))

    compare('evaluation-best.json', filename)

    if args.confusion_matrix:
        cm = confusion_matrix(y_true, y_pred, labels=unique_labels)
        plot_confusion_matrix(cm, unique_labels, normalize=True)
        plt.show()
