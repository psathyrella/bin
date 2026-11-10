"""Parsing for the hangboard training logs in Dropbox/hill/training/<year>/hangboard.txt.

Two log formats are supported, chosen by the 'config:' line at the top of each file:

  full  (2018-2025)  one weight per set, both hands together, and an explicit
                     fail second/rep/set triple when I didn't finish.
  light (2026-)      one 'L/R' weight per set, and a trailing 'x' on any set I
                     didn't finish (recording a weight at all means I got to
                     within a rep of the end).

See read_grip_line() for the grip line grammar.
"""
import calendar
import collections
import copy
import math
import re
from datetime import datetime

import yaml

# ----------------------------------------------------------------------------------------
fail_cfg = ['fail-second', 'fail-rep', 'fail-set']
all_grips = set(['half crimp', 'MR', 'MRP', 'thin pinch', 'full crimp', 'IM', 'IMR', 'RP', 'med pinch', 'wide pinch'])
extra_completion_strs = ['completed', 'barely', 'too easy', 'little easy', 'pretty easy']  # phrases i have used at some point that indicate i finished the set (ick)
min_weight_increment = 5  # minimum weight increment between sets/workouts

# config keys beyond n_sets/n_reps/work_time/rest_time, with the values that reproduce the old format
cfg_defaults = {
    'hands': 'both',        # 'both': one weight per set; 'separate': every weight is written 'L/R'
    'set_increment': None,  # weight added between successive sets; if set, one weight per grip line expands to all sets
    'mark_fails': 'full',   # 'full': fail second/rep/set triple; 'light': trailing 'x' on each set I didn't finish
    'mode': 'hang',         # 'hang': body weight is part of the load; 'lift': it isn't (picking weight up off the ground)
}
hand_names = {'both': ['both'], 'separate': ['L', 'R']}
skip_strs = ['skip', 'skipped']

# ----------------------------------------------------------------------------------------
# bash color codes
Colors = {}
Colors['head'] = '\033[95m'
Colors['bold'] = '\033[1m'
Colors['purple'] = '\033[95m'
Colors['blue'] = '\033[94m'
Colors['light_blue'] = '\033[1;34m'
Colors['green'] = '\033[92m'
Colors['yellow'] = '\033[93m'
Colors['red'] = '\033[91m'
Colors['reverse_video'] = '\033[7m'
Colors['red_bkg'] = '\033[41m'
Colors['end'] = '\033[0m'

# ----------------------------------------------------------------------------------------
def color(col, seq, width=None, padside='left'):
    if col is None:
        return seq
    return_str = [Colors[col], seq, Colors['end']]
    if width is not None:  # make sure final string prints to correct width
        n_spaces = max(0, width - len(seq))  # if specified <width> is greater than uncolored length of <seq>, pad with spaces so that when the colors show up properly the colored sequences prints with width <width>
        if padside == 'left':
            return_str.insert(0, n_spaces * ' ')
        elif padside == 'right':
            return_str.insert(len(return_str), n_spaces * ' ')
        else:
            assert False
    return ''.join(return_str)

# ----------------------------------------------------------------------------------------
num_str = r'(?:[-+]?\d+(?:\.\d+)?|-)'  # a weight, or a dash for a set I didn't do
both_wtok = re.compile(r'^(%s)(x?)$' % num_str)
sep_wtok = re.compile(r'^(%s)(x?)/(%s)(x?)$' % (num_str, num_str))

# ----------------------------------------------------------------------------------------
def parse_config(line, debug=False):
    cfgfo = yaml.load(line.lstrip('config: '), Loader=yaml.CLoader)
    for key, val in cfg_defaults.items():
        cfgfo.setdefault(key, val)
    assert cfgfo['n_sets'] == len(cfgfo['n_reps'])
    for key in ['hands', 'mark_fails', 'mode']:
        allowed = {'hands': list(hand_names), 'mark_fails': ['full', 'light'], 'mode': ['hang', 'lift']}[key]
        if cfgfo[key] not in allowed:
            raise Exception('unexpected config value \'%s\' for \'%s\' (choose from %s)' % (cfgfo[key], key, allowed))
    if cfgfo['set_increment'] is not None and cfgfo['mark_fails'] == 'full':
        raise Exception('set_increment isn\'t supported in the old \'full\' fail format (it would be ambiguous with the fail triple)')
    if debug:
        print('  config: %s' % cfgfo)
    return cfgfo

# ----------------------------------------------------------------------------------------
def hands(cfgfo):
    return hand_names[cfgfo['hands']]

# ----------------------------------------------------------------------------------------
def is_lift(cfgfo):
    return cfgfo['mode'] == 'lift'

# ----------------------------------------------------------------------------------------
def read_grip_name(lstrs, line):
    grip = lstrs.pop(0)
    if grip not in all_grips and len(lstrs) > 0:
        grip += ' ' + lstrs.pop(0)
    if grip not in all_grips:
        raise Exception('couldn\'t find grip in line \'%s\'' % line)
    return grip

# ----------------------------------------------------------------------------------------
def n_sets_for_line(line, cfgfo):  # grip lines can override the file-wide set count with N_SETS:N
    if 'N_SETS' in line:
        return int([l for l in line.split() if 'N_SETS' in l][0].split(':')[1])
    return cfgfo['n_sets']

# ----------------------------------------------------------------------------------------
def make_set(cfgfo, weights, failed=None):  # one set: {hand : {'weight' : w, 'failed' : bool or None}}
    return {h: {'weight': weights[h], 'failed': None if failed is None else failed[h]} for h in hands(cfgfo)}

# ----------------------------------------------------------------------------------------
def read_full_weights(lstrs, gfo, cfgfo, n_sets, hfname, iline, line):
    """Old format: <n_sets> bare weights, positionally, a dash for any set I skipped."""
    gfo['added-weights'] = []
    for iset in range(n_sets):
        if len(lstrs) == 0:
            print('  %s not enough weights in %s at line %d (expected %d sets, got %d -- put a dash for any skipped sets):\n  %s' % (color('red', 'error'), hfname, iline + 1, n_sets, iset, line.rstrip()))
            break
        twgt = lstrs.pop(0)
        gfo['added-weights'].append(float('nan') if twgt == '-' else float(twgt))
    gfo['sets'] = [make_set(cfgfo, {'both': w}) for w in gfo['added-weights']]

# ----------------------------------------------------------------------------------------
def read_light_weights(lstrs, gfo, cfgfo, n_sets, hfname, iline, line):
    """New format: a weight per set, each written 'L/R' if hands are separate, with a
    trailing 'x' on any set I didn't finish. If set_increment is configured, a single
    weight expands to all <n_sets> sets, and an 'x' on it marks the last (heaviest) set."""
    wtok_re = sep_wtok if cfgfo['hands'] == 'separate' else both_wtok
    wtoks = []
    while len(lstrs) > 0 and len(wtoks) < n_sets and wtok_re.match(lstrs[0]):
        wtoks.append(wtok_re.match(lstrs.pop(0)).groups())

    def wgts(groups):  # a matched token -> weight and fail flag per hand
        pairs = [groups[i:i + 2] for i in range(0, len(groups), 2)]
        return ({h: float('nan') if w == '-' else float(w) for h, (w, _) in zip(hands(cfgfo), pairs)},
                {h: x == 'x' for h, (_, x) in zip(hands(cfgfo), pairs)})

    if len(wtoks) == n_sets:
        gfo['sets'] = [make_set(cfgfo, *wgts(g)) for g in wtoks]
    elif len(wtoks) == 1 and cfgfo['set_increment'] is not None:  # expand one weight into the whole ladder
        base, failed = wgts(wtoks[0])
        gfo['sets'] = [make_set(cfgfo, {h: base[h] + iset * cfgfo['set_increment'] for h in base},
                                {h: failed[h] and iset == n_sets - 1 for h in failed})
                       for iset in range(n_sets)]
    else:
        print('  %s expected %d weights (or 1 to expand by set_increment) in %s at line %d, but got %d:\n  %s' % (color('red', 'error'), n_sets, hfname, iline + 1, len(wtoks), line.rstrip()))
        gfo['sets'] = []
    gfo['sent'] = 'no' if any(s[h]['failed'] for s in gfo['sets'] for h in s) else 'yes'

# ----------------------------------------------------------------------------------------
def read_full_fail_info(lstrs, gfo):
    """Old format: 'sent', or the second/rep/set on which I failed."""
    if ' '.join(lstrs[0:2]) == 'fail at':
        lstrs = lstrs[2:]
    if len(lstrs) > 0 and lstrs[0] == 'sent':  # new style: make it explicit
        gfo['sent'] = 'yes'
        lstrs.pop(0)
    elif len(lstrs) > 3 and lstrs[1] == 'on' and lstrs[3] == 'of':
        gfo['fail-second'] = int(lstrs[0].rstrip('s'))
        gfo['fail-rep'] = int(lstrs[2])
        gfo['fail-set'] = int(lstrs[4])
        lstrs = lstrs[5:]
    elif len(re.compile('[0-9][0-9][0-9]').findall(''.join(lstrs[:3]))) > 0:  # first three items are three single digit integers
        for tstr in fail_cfg:
            gfo[tstr] = int(lstrs.pop(0))
    elif len(lstrs) == 0:  # old style (less clear)
        gfo['sent'] = 'yes'
    else:
        gfo['sent'] = 'unknown'  # i parse the note below, which can change this
    return lstrs

# ----------------------------------------------------------------------------------------
def read_grip_line(line, cfgfo, hfname='', iline=0, debug=False):
    """Parse one grip line, e.g. (old) 'MR  -65 -55 fail at 9s on 4 of 2' or
    (new) 'MR  -65/-60x'. Returns None for grips I skipped entirely."""
    lstrs = line.strip().split()
    gfo = {'grip': read_grip_name(lstrs, line), 'sent': 'no'}
    if any(s in lstrs for s in skip_strs):
        gfo['skipped'] = True
        if debug:
            print('     %10s   %s' % (gfo['grip'], color('red', 'skipped')))
        return None

    n_sets = n_sets_for_line(line, cfgfo)
    if cfgfo['mark_fails'] == 'full':
        read_full_weights(lstrs, gfo, cfgfo, n_sets, hfname, iline, line)
    else:
        read_light_weights(lstrs, gfo, cfgfo, n_sets, hfname, iline, line)

    if 'N_REPS' in line or 'WORK_TIME' in line or 'REST_TIME' in line:
        raise Exception('not yet implemented')

    if cfgfo['mark_fails'] == 'full':
        lstrs = read_full_fail_info(lstrs, gfo)
    gfo['note'] = ' '.join(lstrs)

    if gfo['sent'] == 'unknown' and any(e in gfo['note'] for e in extra_completion_strs):
        gfo['sent'] = 'yes'
        if debug:
            for estr in [e for e in extra_completion_strs if e in gfo['note']]:
                gfo['note'] = gfo['note'].replace(estr, color('green', estr))
    if 'NEW_GRIP' in gfo['note'] and debug:
        print('    %s changed %s grip (see note)' % (color('red', 'note'), gfo['grip']))
    return gfo

# ----------------------------------------------------------------------------------------
def print_grip_line(gfo, cfgfo):
    if gfo['sent'] == 'unknown':
        sentstr = color('purple', '?')
    elif gfo['sent'] == 'yes':
        sentstr = color('green', 'x')
    else:
        sentstr = ' '
    def fstr(val, eclr=''):
        if math.isnan(val):
            vstr = '%5s' % '-'
        else:
            vstr = '%5.0f' % val if int(val) == val else ' %6.1f' % val
        return color(eclr, vstr) if eclr != '' else vstr
    wrong_n_sets = len(gfo['sets']) != cfgfo['n_sets']
    wstrs = []
    for h in hands(cfgfo):
        wstrs.append(''.join(fstr(s[h]['weight'], 'red' if wrong_n_sets or s[h]['failed'] else '') for s in gfo['sets']))
    print('     %10s    %s   %s   %s  %s' % (gfo['grip'], '  '.join(wstrs), sentstr, ' '.join(str(gfo[f] if f in gfo else color('purple', '-')) for f in fail_cfg), gfo['note']))

# ----------------------------------------------------------------------------------------
def init_workout(line, cfgfo, year, debug=False):
    hfo = {}
    lstrs = line.split()
    hfo['session'] = int(lstrs[0].lstrip('>'))
    hfo['date'] = datetime.strptime('%s %s %s' % (lstrs[1].lstrip('('), lstrs[2].rstrip(')').upper(), year), '%d %b %Y')  # for later plotting use
    hfo['grips'] = collections.OrderedDict()
    hfo['cfg'] = copy.deepcopy(cfgfo)
    if len(lstrs) > 3:  # weight, temp, humidity
        for lstr in lstrs[3:]:
            if 'F' in lstr:
                hfo['temp-F'] = int(lstr[:-1])
            elif '%' in lstr:
                hfo['humid'] = int(lstr[:-1])
            else:  # try to figure out if it's weight... I should've added units
                hfo['weight'] = float(lstr)
    if debug:
        print('  %-s  %2d %s %s' % (color('red' if hfo['session'] == 1 else 'blue', 'hb %d' % hfo['session'], width=5, padside='right'), hfo['date'].day, color('red_bkg' if hfo['session'] == 1 else None, calendar.month_abbr[hfo['date'].month]), year))
    return hfo

# ----------------------------------------------------------------------------------------
def read_hfo(hfname, year, n_workouts=None, debug=False):  # n_workouts: stop after reading this many complete workouts (for testing)
    if debug:
        print(' reading %s' % hfname)
    cfgfo = None
    workouts = []
    with open(hfname) as hfile:
        hlines = hfile.readlines()
    hfo = None
    for iline, line in enumerate(hlines):
        if line[0] == '#':
            continue

        if line.find('config:') == 0:
            if cfgfo is not None:
                print('    %s cfg info' % color('red', 'replacing'))
            cfgfo = parse_config(line, debug=debug)
            continue
        elif line[0] == '>':
            hfo = init_workout(line, cfgfo, year, debug=debug)
            continue
        elif len(line.strip()) == 0:  # empty line: end of workout/after initial config line
            if hfo is not None:  # if it's None, we probably just read the config line
                workouts.append(hfo)
                hfo = None
            if n_workouts is not None and len(workouts) >= n_workouts:
                print('  breaking after %d workouts' % n_workouts)
                break
            continue
        elif line.find('next') == 0:
            if debug:
                print('    stopping at \'next:\' block (ignoring %d remaining lines)' % (len(hlines) - iline - 1))
            break

        # actual grip line
        if cfgfo is None:
            raise Exception('didn\'t read config info from %s (line starting with \'config:\')' % hfname)
        gfo = read_grip_line(line, cfgfo, hfname=hfname, iline=iline, debug=debug)
        if gfo is None:  # grip I skipped entirely
            continue
        if hfo is None:
            raise Exception('grip line found but no workout initialized in %s at line %d:\n  %s' % (hfname, iline + 1, line.rstrip()))
        hfo['grips'][gfo['grip']] = gfo
        if debug:
            print_grip_line(gfo, cfgfo)

    if hfo is not None:  # add final workout if file doesn't end with empty line
        workouts.append(hfo)
    return workouts
