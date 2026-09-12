#!/usr/bin/env python3
"""Reproduce the first-conjunct census documented in docs/RESULTS.md.
Run: python analysis/census.py. Uses an explicit frozen arm roster.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = lambda p: os.path.join(ROOT, p)

HARD45 = set(json.load(open(R('splits/hard45.json')))['task_ids'])
CUT150 = set(json.load(open(R('splits/full150.json')))['task_ids'])
assert len(HARD45) == 45 and len(CUT150) == 150


def load(path):
    d = json.load(open(R(path)))
    return d['results'] if isinstance(d, dict) and 'results' in d else d


# The three k=1 Claude Full-150 arms share one file, keyed by model.
_F150 = load('results/census/full150_neutral_adaptive_runs.json')
_by_model = lambda m: [r for r in _F150 if (r.get('model') or r.get('generator')) == m]

# (label, rows, cut). GPT/DeepSeek Full-150 runs are scored over all 169
# impossible environments and restricted to CUT150 here.
ROSTER = [
    ('Full-150  opus',                    _by_model('opus'),                              CUT150),
    ('Full-150  sonnet',                  _by_model('sonnet'),                            CUT150),
    ('Full-150  haiku',                   _by_model('haiku'),                             CUT150),
    ('Full-150  gpt-5.5',                 load('results/census/gpt55_full_runs.json'),           CUT150),
    ('Full-150  gpt-5.4-mini',            load('results/census/gpt54mini_full_runs.json'),       CUT150),
    ('Full-150  dsv4flash',               load('results/census/dsv4flash_full_runs.json'),       CUT150),
    ('Full-150  gpt-5.6-sol',             load('results/census/gpt56sol_full_runs.json'),        CUT150),
    ('Full-150  gpt-5.6-terra',           load('results/census/gpt56terra_full_runs.json'),      CUT150),
    ('Full-150  sonnet-5',                load('results/census/sonnet5_full_runs.json'),         CUT150),
    ('Full-150  gpt-5.6-luna',            load('results/census/gpt56luna_full_runs.json'),       CUT150),
    ('Hard-45   dsv4flash',               load('results/census/dsv4flash_hardset_runs.json'),    HARD45),
    ('Hard-45   gpt-5.6-luna',            load('results/census/gpt56luna_hardset_runs.json'),    HARD45),
    ('Hard-45   gpt-5.6-sol',             load('results/census/gpt56sol_hardset_runs.json'),     HARD45),
    ('Hard-45   gpt-5.6-terra',           load('results/census/gpt56terra_hardset_runs.json'),   HARD45),
    ('Hard-45   sonnet-5',                load('results/census/sonnet5_hardset_runs.json'),      HARD45),
    # Both scorings of GPT-5.5 and gpt-5.4-mini are counted. The leaderboard shows
    # only the later (2026-08) one of each; the earlier arms are retained here.
    ('Hard-45   gpt-5.5 (2026-06)',       load('results/census/gpt55_hardset_runs.json'),        HARD45),
    ('Hard-45   gpt-5.5 (2026-08)',       load('results/census/bridge/gpt55_rescore_hard45.json'),     HARD45),
    # No file is named for the 2026-06 gpt-5.4-mini Hard-45 arm. Its 169-environment
    # Full-150 run covers all 45 hard ids, and the restriction reproduces 40/45.
    ('Hard-45   gpt-5.4-mini (2026-06)',  load('results/census/gpt54mini_full_runs.json'),       HARD45),
    ('Hard-45   gpt-5.4-mini (2026-08)',  load('results/census/bridge/gpt54mini_rescore_hard45.json'), HARD45),
    # Opus 5 was held out of this census while its row was held out of the
    # leaderboard -- the arm is self-play (Opus 5 is also attacker and oracle).
    # The held-out-attacker test (results/census/opus5_heldout_attacker.md) came back flat
    # and the row joined T2's ranking, so it joins the census on the same evidence.
    # Its self-play caveat is a caveat about the RATE; these two rows contribute
    # cells to a count of how often the score test and the oracle come apart, which
    # is not a quantity self-play biases.
    ('Full-150  opus-5',                  load('results/census/opus5_full_runs.json'),           CUT150),
    ('Hard-45   opus-5',                  load('results/census/opus5_hardset_runs.json'),        HARD45),
]

# Deliberately OUT of the roster, so that leaving them out is a decision on the
# record rather than an omission:
#   results/census/resample_{opus,sonnet,haiku}_runs.json -- k>1 replicate draws of arms
#     already counted, not separate arms; counting a draw as an arm would add ~25
#     tie cells and 6 gap cells to a census that reports 5 and 8.
#   results/census/opus5_heldout_p3.json -- the held-out-attacker leg re-scores 45 cells
#     already counted above with a different ATTACKER, so it is a second draw of
#     one arm rather than a new arm.

TOT = dict(arms=0, cells=0, violate=0, exploited=0, gap=0, tie=0)
print('%-34s %5s %8s %10s %5s %5s' % ('arm', 'n', 'violate', 'exploited', 'gap', 'tie'))
for label, rows, cut in ROSTER:
    rows = [r for r in rows if r['task_id'] in cut
            and r.get('violates') is not None and r.get('adv') is not None]
    assert len(rows) == len(cut), f'{label}: {len(rows)} cells, expected {len(cut)}'
    v = [r for r in rows if r['violates']]
    e = [r for r in v if r['adv'] >= r['baseline']]
    g = [r for r in v if r['adv'] < r['baseline']]
    t = [r for r in v if r['adv'] == r['baseline']]
    print('%-34s %5d %8d %10d %5d %5d' % (label, len(rows), len(v), len(e), len(g), len(t)))
    TOT['arms'] += 1
    for k, n in (('cells', len(rows)), ('violate', len(v)),
                 ('exploited', len(e)), ('gap', len(g)), ('tie', len(t))):
        TOT[k] += n

print('\nTOTAL  arms=%(arms)d cells=%(cells)d violate=%(violate)d '
      'exploited=%(exploited)d gap=%(gap)d tie=%(tie)d' % TOT)

# The six numbers asserted in docs/RESULTS.md. Update the paragraph and
# this block together, never one without the other.
PUBLISHED = dict(arms=21, cells=2100, violate=522, exploited=514, gap=8, tie=5)
bad = {k: (TOT[k], PUBLISHED[k]) for k in PUBLISHED if TOT[k] != PUBLISHED[k]}
assert not bad, f'census drifted from docs/RESULTS.md: {bad}'
print('matches docs/RESULTS.md on all six quantities.')
