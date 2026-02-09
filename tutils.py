import sys
import numpy
import traceback
from datetime import datetime, timedelta
import calendar
import copy
import csv

# ----------------------------------------------------------------------------------------
def process_args(args):
    # ----------------------------------------------------------------------------------------
    def process_date(aname):
        if getattr(args, aname) is None:
            return
        # getattr(args, aname) = datetime.fromisoformat('2019-01-04')  # new in python 3.7, darn it
        try:
            setattr(args, aname, datetime.strptime(getattr(args, aname), '%Y-%b-%d'))
        except ValueError:
            raise Exception('--start-date must be of form 2019-Jun-1')
        if args.debug:
            print(getattr(args, aname))
        # Thu May 21 22:03:29 PDT 2015
    # ----------------------------------------------------------------------------------------
    for aname in ['start_date', 'stop_date']:
        process_date(aname)
    args.half_window = timedelta(days=args.half_window)
    if hasattr(args, 'weekly_half_window'):
        args.weekly_half_window = timedelta(days=args.weekly_half_window)

# ----------------------------------------------------------------------------------------
def parsetime(instr, debug=False):
    tstr = instr
    if len(tstr) < 3:
        tstr += ':00'
    if ':' not in tstr:
        tstr = '%s:%s' % (tstr[ : len(tstr) - 2], tstr[len(tstr) - 2 : ])
    try:
        hours, minutes = [int(v) for v in tstr.split(':')]
        returnval = hours + float(minutes) / 60
    except:
        elines = traceback.format_exception(*sys.exc_info())
        print(''.join(10*' '+l for l in elines))
        print('    couldn\'t parse time from \'%s\' (see previous lines)' % instr)
        returnval = None
    if debug:
        print('  %s --> %s --> %.2f' % (instr, tstr, returnval))
    return returnval

# ----------------------------------------------------------------------------------------
def add_float_averages(mfos, yvar, half_window, output_key='float_avgs', debug=False, exclude_dates=None):
    mfos[output_key] = []
    last_dtime = None  # just for dbg
    for idt, (dtime, wgt) in enumerate(zip(mfos['dates'], mfos[yvar])):
        wgtlist, dtlist = [], []  # <dtlist> is just for dbg

        # first go backward in time til you've gone outside the window
        itmp = idt
        while True:
            if exclude_dates is None or mfos['dates'][itmp] not in exclude_dates:
                wgtlist.append(mfos[yvar][itmp])
                dtlist.append(mfos['dates'][itmp])
            itmp -= 1
            if itmp < 0 or (dtime - mfos['dates'][itmp]) > half_window:
                break

        # then do the same thing forward
        itmp = idt + 1
        while True:
            if itmp >= len(mfos['dates']) or (mfos['dates'][itmp] - dtime) > half_window:
                break
            if exclude_dates is None or mfos['dates'][itmp] not in exclude_dates:
                wgtlist.append(mfos[yvar][itmp])
                dtlist.append(mfos['dates'][itmp])
            itmp += 1

        if len(wgtlist) > 0:
            mfos[output_key].append(sum(wgtlist) / len(wgtlist))
        else:
            mfos[output_key].append(0)
        if debug:
            # ----------------------------------------------------------------------------------------
            def dfcn(attr):
                if last_dtime is None or getattr(dtime, attr) != getattr(last_dtime, attr):
                    return str(getattr(dtime, attr))
                else:
                    return ''
            # ----------------------------------------------------------------------------------------
            def dstr(tmpdt):
                tmp_ddays = (tmpdt - dtime).total_seconds()/(24.*60*60)
                # return ('%.'+str(2 if tmp_ddays < 1 else 0)+'f') % tmp_ddays
                return '%4.1f' % tmp_ddays
            # ----------------------------------------------------------------------------------------
            print('    %4s %3s %3s     %-22s   %s  (total: %d)' % (dfcn('year'), dfcn('month'), dfcn('day'), ' '.join('%2d'%dt.day for dt in sorted(dtlist)), ' '.join(dstr(dt) for dt in sorted(dtlist)), len(wgtlist)))
        last_dtime = dtime

# ----------------------------------------------------------------------------------------
def plot_mfos(args, mfos, yvar, end_date=None, tickday=1, vacation_dates=None, avg_hrs_per_week=None):
    if end_date is None:
        end_date = mfos['dates'][-1]
    xticks, xticklabels = [], []
    tmp_date = copy.deepcopy(args.start_date)
    tickmonths = list(range(1, 13)) if (end_date - args.start_date) < timedelta(days=500) else list(range(1, 13, 2))
    while tmp_date < end_date:
        if tmp_date.day == tickday and tmp_date.month in tickmonths:
            xticks.append((tmp_date - args.start_date).days)
            xtl = '%s %d' % (calendar.month_abbr[tmp_date.month], tickday)
            if tmp_date.month == 1:
                xtl = '%d %s' % (tmp_date.year, xtl)
            xticklabels.append(xtl)
        tmp_date += timedelta(days=1)
    # for dates, weights in mfos.values():


    # ----------------------------------------------------------------------------------------
    import matplotlib as mpl
    mpl.use('Agg')
    mpl.rcParams['svg.fonttype'] = 'none'
    import matplotlib.pyplot as plt
    import seaborn
    seaborn.set_style('ticks')
    fsize = 20
    mpl.rcParams.update({
        # 'legend.fontweight': 900,
        'legend.fontsize': fsize,
        'axes.titlesize': fsize,
        # 'axes.labelsize': fsize,
        'xtick.labelsize': fsize,
        'ytick.labelsize': fsize,
        'axes.labelsize': fsize
    })


    dpi = 80
    xpixels, ypixels = 2500, 500
    fig, ax = plt.subplots(figsize=(xpixels / dpi, ypixels / dpi))
    fig.tight_layout()
    plt.gcf().subplots_adjust(bottom=0.27, left=0.06, right=0.94, top=0.92)

    ax.plot(mfos['n_days'], mfos[yvar], linewidth=0, alpha=0.7, markersize=15, marker='.', label=yvar)
    ax.plot(mfos['n_days'], mfos['float_avgs'], linewidth=3, alpha=0.6, label='%d-day avg' % (2 * args.half_window.days + 1))
    if yvar == 'weights':
        ax.set_ylabel('weight')
    else:
        ax.axhline(y=5.7, color='tab:orange', linestyle='--', alpha=0.5, linewidth=3)
        ax.set_ylabel('hours/day')
        ax.set_ylim(bottom=0)

    if 'weekly_avgs' in mfos:
        ax2 = ax.twinx()
        ax2.plot(mfos['n_days'], mfos['weekly_avgs'], linewidth=3, alpha=0.6, color='green', label='%d-day avg hrs/week (exclud. vac.)' % (2 * args.weekly_half_window.days + 1))
        ax2.axhline(y=40, color='green', linestyle='--', alpha=0.5, linewidth=3)
        weekly_max = max(v for v in mfos['weekly_avgs'] if not numpy.isnan(v))
        ax2.set_ylim(0, weekly_max * 1.15)
        ax2.set_ylabel('hours/week', color='green')
        ax2.tick_params(axis='y', labelcolor='green')

    plt.xticks(xticks)
    ax.grid(axis='y')
    ax.set_xticklabels(xticklabels, rotation='vertical')
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = (ax2.get_legend_handles_labels() if 'weekly_avgs' in mfos else ([], []))
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', bbox_to_anchor=(0, 1.15), ncol=len(lines1) + len(lines2))

    if vacation_dates:
        # group contiguous vacation dates into spans and shade them
        sorted_vdates = sorted(vacation_dates)
        spans = []
        span_start = sorted_vdates[0]
        span_end = sorted_vdates[0]
        for vd in sorted_vdates[1:]:
            if (vd - span_end).days <= 1:
                span_end = vd
            else:
                spans.append((span_start, span_end))
                span_start = vd
                span_end = vd
        spans.append((span_start, span_end))
        for s, e in spans:
            x0 = (s - args.start_date).days - 0.5
            x1 = (e - args.start_date).days + 0.5
            ax.axvspan(x0, x1, alpha=0.15, color='red')
        vac_str = '%d vacation days' % len(sorted_vdates)
        if avg_hrs_per_week is not None:
            vac_str = '%.1f hrs/week avg (exclud. vac.),  %s' % (avg_hrs_per_week, vac_str)
        ax.text(0.98, 1.04, vac_str, transform=ax.transAxes, ha='right', va='bottom', fontsize=18, color='red')

    plt.savefig(args.plotfile)

# ----------------------------------------------------------------------------------------
def read_mfos(args):
    mfos = {'dates' : [], 'weights' : [], 'n_days' : []}
    with open(args.mfile) as csvfile:
        reader = csv.DictReader(csvfile)
        for line in reader:
            dt = datetime.strptime(line['date'].strip(), '%a %b %d %H:%M:%S %Y') #  %Z (was before %Y)
            # epoch = dt.utcfromtimestamp(0)
            if args.start_date is None:
                args.start_date = dt
            elif args.start_date > dt:
                continue
            if args.stop_date is not None and dt > args.stop_date:
                break
            # if len(mfos['dates']) > 0 and mfos['dates'][-1] is not None and dt - mfos['dates'][-1] > max_delta:
            #     mfos['dates'].append(None)
            #     mfos['weights'].append(None)
            #     mfos['n_days'].append(None)
            mfos['dates'].append(dt)
            mfos['weights'].append(float(line['weight']))
            mfos['n_days'].append((dt - args.start_date).total_seconds() / 86400.)

    return mfos
