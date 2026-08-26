"""Tests for hangutils/hangplot: run with 'pytest test_hangutils.py' from ~/bin.

Two halves:
  - the new (2026-) 'light' format, on synthetic logs written to a tmpdir
  - the old (2018-2025) 'full' format, checked against test-data/golden_legacy.json, which was
    dumped from the pre-refactor hangplot. Three grip entries differ on purpose (see
    known_skip_fixes): they say 'skip' rather than 'skipped', which the old code missed.
"""
import json
import math
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hangutils

bindir = os.path.dirname(os.path.abspath(__file__))
training_dir = '%s/Dropbox/hill/training' % os.getenv('HOME')
legacy_years = ['2018', '2019', '2020', '2022', '2023', '2024', '2025']

new_cfg_line = 'config: {n_sets: 3, n_reps: [7, 6, 6], work_time: 10, rest_time: 5, hands: separate, set_increment: 10, mark_fails: light, mode: lift}\n'
old_cfg_line = 'config: {n_sets: 2, n_reps: [7, 6], work_time: 10, rest_time: 5}\n'

# ----------------------------------------------------------------------------------------
def cfg(**kwargs):
    kfo = dict(n_sets=3, n_reps='[7, 6, 6]', work_time=10, rest_time=5, hands='separate', set_increment=10, mark_fails='light', mode='lift')
    kfo.update(kwargs)
    return hangutils.parse_config('config: {%s}' % ', '.join('%s: %s' % (k, v) for k, v in kfo.items()))

# ----------------------------------------------------------------------------------------
def grip(line, cfgfo=None, **kwargs):
    return hangutils.read_grip_line(line, cfgfo if cfgfo is not None else cfg(**kwargs))

# ----------------------------------------------------------------------------------------
def wgts(gfo, hand):
    return [s[hand]['weight'] for s in gfo['sets']]

# ----------------------------------------------------------------------------------------
def fails(gfo, hand):
    return [s[hand]['failed'] for s in gfo['sets']]

# ----------------------------------------------------------------------------------------
def write_log(tmpdir, cfg_line, body, year='2026'):
    ydir = os.path.join(str(tmpdir), year)
    os.makedirs(ydir, exist_ok=True)
    fname = os.path.join(ydir, 'hangboard.txt')
    with open(fname, 'w') as tfile:
        tfile.write(cfg_line + '\n' + body)
    return fname


# ----------------------------------------------------------------------------------------
# new 'light' format
# ----------------------------------------------------------------------------------------
def test_one_weight_expands_by_set_increment():
    gfo = grip('half crimp      55/50')
    assert wgts(gfo, 'L') == [55, 65, 75]
    assert wgts(gfo, 'R') == [50, 60, 70]
    assert gfo['sent'] == 'yes'
    assert gfo['note'] == ''

def test_set_increment_is_configurable():
    assert wgts(grip('MR   55/50', set_increment=5), 'L') == [55, 60, 65]
    assert wgts(grip('MR   55/50', set_increment=2.5), 'L') == [55, 57.5, 60]

def test_explicit_sets_are_taken_literally():
    gfo = grip('half crimp      55/50  65/60  70/62.5')
    assert wgts(gfo, 'L') == [55, 65, 70]
    assert wgts(gfo, 'R') == [50, 60, 62.5]

def test_half_pound_weights():
    gfo = grip('MRP   52.5/47.5')
    assert wgts(gfo, 'L') == [52.5, 62.5, 72.5]
    assert wgts(gfo, 'R') == [47.5, 57.5, 67.5]

def test_x_on_expanded_weight_marks_only_the_last_set():
    gfo = grip('half crimp      55/50x')
    assert fails(gfo, 'L') == [False, False, False]
    assert fails(gfo, 'R') == [False, False, True]
    assert wgts(gfo, 'R') == [50, 60, 70]  # the x doesn't disturb the ladder
    assert gfo['sent'] == 'no'

def test_x_on_explicit_sets_marks_that_set_and_hand():
    gfo = grip('half crimp      55/50  65x/60  75/70')
    assert fails(gfo, 'L') == [False, True, False]
    assert fails(gfo, 'R') == [False, False, False]
    assert gfo['sent'] == 'no'

def test_both_hands_can_fail_the_same_set():
    gfo = grip('MR   55/50  65x/60x  75/70')
    assert fails(gfo, 'L') == [False, True, False]
    assert fails(gfo, 'R') == [False, True, False]

def test_dash_skips_one_hand():
    gfo = grip('MR   55/-')
    assert wgts(gfo, 'L') == [55, 65, 75]
    assert all(math.isnan(w) for w in wgts(gfo, 'R'))

def test_dash_skips_one_set_of_one_hand():
    gfo = grip('MR   55/50  65/60  75/-')
    assert math.isnan(wgts(gfo, 'R')[2])
    assert wgts(gfo, 'R')[:2] == [50, 60]

def test_negative_weights_still_parse():  # in case I ever go back to hanging with counterweight
    gfo = grip('half crimp      -110/-105', mode='hang')
    assert wgts(gfo, 'L') == [-110, -100, -90]
    assert wgts(gfo, 'R') == [-105, -95, -85]

def test_note_is_kept():
    gfo = grip('MR   55/50  felt tweaky in the left ring finger')
    assert gfo['note'] == 'felt tweaky in the left ring finger'
    assert wgts(gfo, 'L') == [55, 65, 75]

def test_n_sets_override():
    gfo = grip('med pinch   55/50  N_SETS:2')
    assert wgts(gfo, 'L') == [55, 65]
    assert gfo['note'] == 'N_SETS:2'

def test_skipped_grip_returns_none():
    assert grip('med pinch   skip') is None
    assert grip('med pinch   skipped (skin)') is None

def test_hands_both_with_light_format():
    gfo = grip('half crimp      55x', hands='both')
    assert wgts(gfo, 'both') == [55, 65, 75]
    assert fails(gfo, 'both') == [False, False, True]

def test_wrong_number_of_weights_is_reported(capsys):
    gfo = grip('half crimp      55/50  65/60')  # 2 weights, 3 sets
    assert gfo['sets'] == []
    assert 'expected 3 weights' in capsys.readouterr().out

def test_multi_word_grip_names():
    assert grip('med pinch   55/50')['grip'] == 'med pinch'
    assert grip('full crimp   55/50')['grip'] == 'full crimp'

def test_unknown_grip_raises():
    with pytest.raises(Exception, match='couldn\'t find grip'):
        grip('sloper   55/50')

def test_bad_config_values_raise():
    with pytest.raises(Exception, match='unexpected config value'):
        cfg(hands='either')
    with pytest.raises(Exception, match='unexpected config value'):
        cfg(mode='floating')
    with pytest.raises(AssertionError):
        cfg(n_sets=3, n_reps='[7, 6]')

def test_set_increment_rejected_in_old_format():
    with pytest.raises(Exception, match='set_increment'):
        hangutils.parse_config('config: {n_sets: 2, n_reps: [7, 6], work_time: 10, rest_time: 5, set_increment: 10}')

def test_new_format_workout_round_trip(tmpdir):
    fname = write_log(tmpdir, new_cfg_line, '\n'.join([
        '>1 (3 jan) 181.5 55F',
        '# a comment inside the workout',
        'half crimp      55/50',
        'MR              45/42.5x',
        'med pinch       skip',
        '',
        '>2 (6 jan) 180.0',
        'half crimp      55/50  65/60  75/70',
        '',
        'next:',
        'half crimp      60/55',
        '']))
    workouts = hangutils.read_hfo(fname, '2026')
    assert len(workouts) == 2  # the 'next:' block is not a workout
    first = workouts[0]
    assert first['session'] == 1 and first['weight'] == 181.5 and first['temp-F'] == 55
    assert first['date'].strftime('%Y-%m-%d') == '2026-01-03'
    assert list(first['grips']) == ['half crimp', 'MR']  # skipped grip dropped
    assert wgts(first['grips']['MR'], 'R') == [42.5, 52.5, 62.5]
    assert fails(first['grips']['MR'], 'R') == [False, False, True]
    assert first['cfg']['mode'] == 'lift' and first['cfg']['hands'] == 'separate'


# ----------------------------------------------------------------------------------------
# old 'full' format
# ----------------------------------------------------------------------------------------
def old_grip(line):
    return hangutils.read_grip_line(line, hangutils.parse_config(old_cfg_line))

def test_old_format_fail_triple():
    gfo = old_grip('half crimp      -25 -15 8 5 2')
    assert gfo['added-weights'] == [-25, -15]
    assert (gfo['fail-second'], gfo['fail-rep'], gfo['fail-set']) == (8, 5, 2)
    assert gfo['sent'] == 'no'

def test_old_format_fail_at_phrasing():
    gfo = old_grip('MR              -65 -55 fail at 9s on 4 of 2')
    assert (gfo['fail-second'], gfo['fail-rep'], gfo['fail-set']) == (9, 4, 2)

def test_old_format_sent_and_dash():
    assert old_grip('IM              -75 - sent')['sent'] == 'yes'
    assert math.isnan(old_grip('IM              -75 - sent')['added-weights'][1])

def test_old_format_note_only_is_unknown():
    gfo = old_grip('med pinch       -70 -60 felt weird')
    assert gfo['sent'] == 'unknown' and gfo['note'] == 'felt weird'

def test_old_format_completion_phrases():
    assert old_grip('med pinch       -70 -60 too easy')['sent'] == 'yes'

def test_old_format_n_sets_override():
    assert old_grip('med pinch       -85 -75 -65  N_SETS:3')['added-weights'] == [-85, -75, -65]

@pytest.mark.parametrize('year', legacy_years)
def test_legacy_files_match_golden(year):
    """The pre-refactor parser's output, field for field, on the real log files."""
    golden = json.load(open('%s/test-data/golden_legacy.json' % bindir))[year]
    workouts = hangutils.read_hfo('%s/%s/hangboard.txt' % (training_dir, year), year)
    assert len(workouts) == len(golden)
    for gold, hfo in zip(golden, workouts):
        assert hfo['session'] == gold['session']
        assert hfo['date'].strftime('%Y-%m-%d') == gold['date']
        # the one intentional change: lines whose note is just 'skip' are now dropped like
        # 'skipped' ones, instead of being read as a real set (2023 MR, 2025 MR and IM)
        expected = [g for g, gf in gold['grips'].items() if not set(hangutils.skip_strs) & set(gf['note'].split())]
        assert list(hfo['grips']) == expected
        for gname in expected:
            gfo, ggold = hfo['grips'][gname], gold['grips'][gname]
            for key, gval in ggold.items():
                assert nanless(gfo[key]) == nanless(gval), '%s %d %s %s' % (year, gold['session'], gname, key)

def nanless(val):  # json round-trips nan, but nan != nan
    if isinstance(val, list):
        return [nanless(v) for v in val]
    return 'nan' if isinstance(val, float) and math.isnan(val) else val

def test_golden_covers_every_grip_entry():  # guard against the golden file silently emptying out
    golden = json.load(open('%s/test-data/golden_legacy.json' % bindir))
    assert sum(len(w['grips']) for year in golden.values() for w in year) == 1068

def test_legacy_sets_mirror_added_weights():
    gfo = old_grip('half crimp      -25 -15 8 5 2')
    assert [s['both']['weight'] for s in gfo['sets']] == gfo['added-weights']
    assert all(s['both']['failed'] is None for s in gfo['sets'])  # per-set fail info doesn't exist in the old format


# ----------------------------------------------------------------------------------------
# end to end
# ----------------------------------------------------------------------------------------
def run_hangplot(*extra):
    return subprocess.run([sys.executable, '%s/hangplot' % bindir] + list(extra), capture_output=True, text=True, cwd=bindir)

def test_hangplot_makes_new_format_plots(tmpdir):
    write_log(tmpdir, new_cfg_line, '\n'.join([
        '>1 (3 jan) 181.5', 'half crimp      55/50', 'MR   45/42.5x', '',
        '>2 (6 jan) 180.0', 'half crimp      60/55', 'MR   45/45', '',
        '>3 (9 jan) 180.0', 'half crimp      60/55x', 'MR   50/-', '']))
    plotdir = os.path.join(str(tmpdir), 'plots')
    res = run_hangplot('--years', '2026', '--training-dir', str(tmpdir), '--plotdir', plotdir, '--plot-grips', 'half-crimp:MR')
    assert res.returncode == 0, res.stderr
    assert sorted(os.listdir(plotdir)) == ['MR.svg', 'half-crimp.svg']
    assert os.path.getsize(os.path.join(plotdir, 'MR.svg')) > 1000

def test_hangplot_makes_legacy_plots(tmpdir):
    plotdir = os.path.join(str(tmpdir), 'plots')
    res = run_hangplot('--plotdir', plotdir, '--plot-grips', 'half-crimp:MR')
    assert res.returncode == 0, res.stderr
    assert sorted(os.listdir(plotdir)) == ['MR.svg', 'half-crimp.svg']

def test_hangplot_refuses_to_mix_formats(tmpdir):
    write_log(tmpdir, new_cfg_line, '>1 (3 jan)\nhalf crimp      55/50\n')
    write_log(tmpdir, old_cfg_line, '>1 (3 jan)\nhalf crimp      -25 -15 sent\n', year='2025')
    res = run_hangplot('--years', '2025:2026', '--training-dir', str(tmpdir), '--plotdir', os.path.join(str(tmpdir), 'plots'))
    assert res.returncode != 0 and 'old- and new-format' in res.stderr

def test_hangplot_refuses_body_weight_for_lift(tmpdir):
    write_log(tmpdir, new_cfg_line, '>1 (3 jan) 181.5\nhalf crimp      55/50\n')
    res = run_hangplot('--years', '2026', '--training-dir', str(tmpdir), '--plotdir', os.path.join(str(tmpdir), 'plots'), '--add-body-weight')
    assert res.returncode != 0 and 'add-body-weight' in res.stderr

def test_real_2026_file_parses():
    hangutils.read_hfo('%s/2026/hangboard.txt' % training_dir, '2026')
