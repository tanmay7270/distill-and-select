import numpy as np
import pickle as pk

from collections import OrderedDict
from sklearn.metrics import average_precision_score
        

class CC_WEB_VIDEO(object):

    def __init__(self):
        with open('datasets/cc_web_video.pickle', 'rb') as f:
            dataset = pk.load(f)
        self.name = 'CC_WEB_VIDEO'
        self.index = dataset['index']
        self.queries = list(dataset['queries'])
        self.database = sorted(list(map(str, self.index.keys())))
        self.ground_truth = dataset['ground_truth']
        self.excluded = dataset['excluded']
        
    def get_queries(self):
        return self.queries

    def get_database(self):
        return self.database

    def calculate_mAP(self, similarities, all_db, all_videos=False, clean=False, positive_labels='ESLMV'):
        mAP = 0.0
        for query_set, labels in enumerate(self.ground_truth):
            query_id = self.queries[query_set]
            i, ri, s = 0.0, 0.0, 0.0
            if query_id in similarities:
                res = similarities[query_id]
                if isinstance(res, (np.ndarray, np.generic)):
                    res = {v: s for v, s in zip(self.database, res) if v in all_db}
                for video_id in sorted(res.keys(), key=lambda x: res[x], reverse=True):
                    if video_id not in self.index: continue
                    video = self.index[video_id]
                    if (all_videos or video in labels) and (not clean or video not in self.excluded[query_set]):
                        ri += 1
                        if video in labels and labels[video] in positive_labels:
                            i += 1.0
                            s += i / ri
                positives = np.sum([1.0 for k, v in labels.items() if
                                    v in positive_labels and (not clean or k not in self.excluded[query_set])])
                mAP += s / positives
        return mAP / len(set(self.queries).intersection(similarities.keys()))

    def evaluate(self, similarities, all_db=None, verbose=True):
        if all_db is None:
            all_db = set(self.database)

        if verbose:
            print('=' * 5, 'CC_WEB_VIDEO Dataset', '=' * 5)
            not_found = len(set(self.queries) - similarities.keys())
            if not_found > 0:
                print(
                    f'[WARNING] {not_found} queries are missing from the results and will be ignored'
                )
            print(f'Queries: {len(similarities)} videos')
            print(f'Database: {len(all_db)} videos')

        mAP = self.calculate_mAP(similarities, all_db, all_videos=False, clean=False)
        mAP_star = self.calculate_mAP(similarities, all_db, all_videos=True, clean=False)
        if verbose:
            print('-' * 25)
            print('All dataset')
            print('CC_WEB mAP: {:.4f}\nCC_WEB* mAP: {:.4f}\n'.format(mAP, mAP_star))

        mAP_c = self.calculate_mAP(similarities, all_db, all_videos=False, clean=True)
        mAP_c_star = self.calculate_mAP(similarities, all_db, all_videos=True, clean=True)
        if verbose:
            print('Clean dataset')
            print('CC_WEB mAP: {:.4f}\nCC_WEB* mAP: {:.4f}'.format(mAP_c, mAP_c_star))
        return {'mAP': mAP, 'mAP_star': mAP_star, 'mAP_c': mAP_c, 'mAP_c_star': mAP_c_star}


class FIVR(object):

    def __init__(self, version='200k', audio=False):
        self.version = version
        self.audio = audio
        with open('datasets/fivr.pickle', 'rb') as f:
            dataset = pk.load(f)
        self.name = 'FIVR'
        self.annotation = dataset['annotation']
        if not self.audio:
            self.queries = sorted(list(dataset[self.version]['queries']))
        else:
            self.queries = sorted([q for q in dataset[self.version]['queries'] if 'DA' in self.annotation[q]])
        self.database = sorted(list(dataset[self.version]['database']))

    def get_queries(self):
        return self.queries

    def get_database(self):
        return self.database

    def calculate_mAP(self, query, res, all_db, relevant_labels):
        gt_sets = self.annotation[query]
        query_gt = set(
            sum(
                (gt_sets[label] for label in relevant_labels if label in gt_sets),
                [],
            )
        )
        query_gt = query_gt.intersection(all_db)

        i, ri, s = 0.0, 0, 0.0
        for video in sorted(res.keys(), key=lambda x: res[x], reverse=True):
            if video != query and video in all_db:
                ri += 1
                if video in query_gt:
                    i += 1.0
                    s += i / ri
        return s / len(query_gt)

    def evaluate(self, similarities, all_db=None, verbose=True):
        if all_db is None:
            all_db = set(self.database)
        else:
            all_db = set(self.database).intersection(all_db)

        if not self.audio:
            DSVR, CSVR, ISVR = [], [], []
            for query, res in similarities.items():
                if query in self.queries:
                    if isinstance(res, (np.ndarray, np.generic)):
                        res = {v: s for v, s in zip(self.database, res) if v in all_db}
                    DSVR.append(self.calculate_mAP(query, res, all_db, relevant_labels=['ND', 'DS']))
                    CSVR.append(self.calculate_mAP(query, res, all_db, relevant_labels=['ND', 'DS', 'CS']))
                    ISVR.append(self.calculate_mAP(query, res, all_db, relevant_labels=['ND', 'DS', 'CS', 'IS']))
            if verbose:
                print('=' * 5, f'FIVR-{self.version.upper()} Dataset', '=' * 5)
                not_found = len(set(self.queries) - similarities.keys())
                if not_found > 0:
                    print(
                        f'[WARNING] {not_found} queries are missing from the results and will be ignored'
                    )

                print(f'Queries: {len(similarities)} videos')
                print(f'Database: {len(all_db)} videos')

                print('-' * 16)
                print('DSVR mAP: {:.4f}'.format(np.mean(DSVR)))
                print('CSVR mAP: {:.4f}'.format(np.mean(CSVR)))
                print('ISVR mAP: {:.4f}'.format(np.mean(ISVR)))
            return {'DSVR': np.mean(DSVR), 'CSVR': np.mean(CSVR), 'ISVR': np.mean(ISVR)}
        else:
            DAVR = []
            for query, res in similarities.items():
                if query in self.queries:
                    if isinstance(res, (np.ndarray, np.generic)):
                        res = {v: s for v, s in zip(self.database, res) if v in all_db}
                    DAVR.append(self.calculate_mAP(query, res, all_db, relevant_labels=['DA']))
            if verbose:
                print('=' * 5, f'FIVR-{self.version.upper()} Dataset', '=' * 5)
                not_found = len(set(self.queries) - similarities.keys())
                if not_found > 0:
                    print(
                        f'[WARNING] {not_found} queries are missing from the results and will be ignored'
                    )

                print(f'Queries: {len(similarities)} videos')
                print(f'Database: {len(all_db)} videos')

                print('-' * 16)
                print('DAVR mAP: {:.4f}'.format(np.mean(DAVR)))
            return {'DAVR': np.mean(DAVR)}


class EVVE(object):

    def __init__(self):
        with open('datasets/evve.pickle', 'rb') as f:
            dataset = pk.load(f)
        self.name = 'EVVE'
        self.events = dataset['annotation']
        self.queries = sorted(list(dataset['queries']))
        self.database = sorted(list(dataset['database']))
        self.query_to_event = {qname: evname
                               for evname, (queries, _, _) in self.events.items()
                               for qname in queries}

    def get_queries(self):
        return self.queries

    def get_database(self):
        return self.database

    def score_ap_from_ranks_1(self, ranks, nres):
        """ Compute the average precision of one search.
        ranks = ordered list of ranks of true positives (best rank = 0)
        nres  = total number of positives in dataset
        """
        if nres == 0 or ranks == []:
            return 0.0

        ap = 0.0

        # accumulate trapezoids in PR-plot. All have an x-size of:
        recall_step = 1.0 / nres

        for ntp, rank in enumerate(ranks):
            # ntp = nb of true positives so far
            # rank = nb of retrieved items so far

            # y-size on left side of trapezoid:
            precision_0 = 1.0 if rank == 0 else ntp / float(rank)
            # y-size on right side of trapezoid:
            precision_1 = (ntp + 1) / float(rank + 1)
            ap += (precision_1 + precision_0) * recall_step / 2.0
        return ap

    def evaluate(self, similarities, all_db=None, verbose=True):
        results = {e: [] for e in self.events}
        if all_db is None:
            all_db = set(self.database).union(set(self.queries))

        not_found = 0
        for query in self.queries:
            if query not in similarities:
                not_found += 1
            else:
                res = similarities[query]
                if isinstance(res, (np.ndarray, np.generic)):
                    res = {v: s for v, s in zip(self.database, res) if v in all_db}
                evname = self.query_to_event[query]
                _, pos, null = self.events[evname]
                if all_db:
                    pos = pos.intersection(all_db)
                pos_ranks = []

                ri, n_ext = 0.0, 0.0
                for ri, dbname in enumerate(sorted(res.keys(), key=lambda x: res[x], reverse=True)):
                    if dbname in pos:
                        pos_ranks.append(ri - n_ext)
                    if dbname not in all_db:
                        n_ext += 1

                ap = self.score_ap_from_ranks_1(pos_ranks, len(pos))
                results[evname].append(ap)
        if verbose:
            print('=' * 18, 'EVVE Dataset', '=' * 18)
            if not_found > 0:
                print(
                    f'[WARNING] {not_found} queries are missing from the results and will be ignored'
                )
            print(f'Queries: {len(similarities)} videos')
            print(f'Database: {len(all_db - set(self.queries))} videos\n')
            print('-' * 50)
        ap, mAP = [], []
        for evname in sorted(self.events):
            queries, _, _ = self.events[evname]
            nq = len(queries.intersection(all_db))
            ap.extend(results[evname])
            mAP.append(np.sum(results[evname]) / nq)
            if verbose:
                print('{0: <36} '.format(evname), 'mAP = {:.4f}'.format(np.sum(results[evname]) / nq))

        if verbose:
            print('=' * 50)
            print('overall mAP = {:.4f}'.format(np.mean(ap)))
        return {'mAP': np.mean(ap)}


class SVD(object):

    def __init__(self, version='unlabeled'):
        self.name = 'SVD'
        self.ground_truth = self.load_groundtruth('datasets/test_groundtruth')
        self.unlabeled_keys = self.get_unlabeled_keys('datasets/unlabeled-data-id')
        if version == 'labeled':
            self.unlabeled_keys = []
        self.database = []
        for k, v in self.ground_truth.items():
            self.database.extend(list(map(str, v.keys())))
        self.queries = sorted(list(map(str, self.ground_truth.keys())))            
        self.database += self.unlabeled_keys
        self.database = sorted(self.database)

    def load_groundtruth(self, filepath):
        gnds = OrderedDict()
        with open(filepath, 'r') as fp:
            for lines in fp:
                tmps = lines.strip().split(' ')
                qid = tmps[0]
                cid = tmps[1]
                gt = int(tmps[-1])
                if qid not in gnds:
                    gnds[qid] = {cid: gt}
                else:
                    gnds[qid][cid] = gt
        return gnds

    def get_unlabeled_keys(self, filepath):
        videos = []
        with open(filepath, 'r') as fp:
            videos.extend(tmps.strip() for tmps in fp)
        return videos

    def get_queries(self):
        return self.queries

    def get_database(self):
        return self.database

    def evaluate(self, similarities, all_db=None, verbose=True):
        mAP = []
        not_found = len(self.ground_truth.keys() - similarities.keys())
        for query, targets in self.ground_truth.items():
            y_true, y_score = [], []
            res = similarities[query]
            if isinstance(res, (np.ndarray, np.generic)):
                res = {v: s for v, s in zip(self.database, res) if v in all_db}
            for target, label in targets.items():
                if target in all_db:
                    s = res[target]
                    y_true.append(label)
                    y_score.append(s)

            for target in self.unlabeled_keys:
                if target in all_db:
                    s = res[target]
                    y_true.append(0)
                    y_score.append(s)
            mAP.append(average_precision_score(y_true, y_score))
        if verbose:
            print('=' * 5, 'SVD Dataset', '=' * 5)
            if not_found > 0:
                print(
                    f'[WARNING] {not_found} queries are missing from the results and will be ignored'
                )
            print(f'Database: {len(all_db)} videos')

            print('-' * 16)
            print('mAP: {:.4f}'.format(np.mean(mAP)))
        return {'mAP': np.mean(mAP)}
