import sys
import numpy
import traceback
from datetime import datetime, timedelta
import calendar
import copy

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
def add_float_averages(mfos, yvar, half_window, debug=False):
    mfos['float_avgs'] = []
    last_dtime = None  # just for dbg
    for idt, (dtime, wgt) in enumerate(zip(mfos['dates'], mfos[yvar])):
        wgtlist, dtlist = [], []  # <dtlist> is just for dbg

        # first go backward in time til you've gone outside the window
        itmp = idt
        while True:
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
            wgtlist.append(mfos[yvar][itmp])
            dtlist.append(mfos['dates'][itmp])
            itmp += 1

        mfos['float_avgs'].append(numpy.mean(wgtlist))
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
            print('    %4s %3s %3s     %-22s   %s' % (dfcn('year'), dfcn('month'), dfcn('day'), ' '.join('%2d'%dt.day for dt in sorted(dtlist)), ' '.join(dstr(dt) for dt in sorted(dtlist))))
        last_dtime = dtime

# ----------------------------------------------------------------------------------------
def plot_mfos(args, mfos, yvar, end_date=None, tickday=1):
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
    plt.gcf().subplots_adjust(bottom=0.27, left=0.2, right=0.78, top=0.92)

    ax.plot(mfos['n_days'], mfos[yvar], linewidth=0, alpha=0.7, markersize=15, marker='.')
    ax.plot(mfos['n_days'], mfos['float_avgs'], linewidth=3, alpha=0.7)

    plt.xticks(xticks)
    ax.grid(axis='y')
    ax.tick_params(labelright=True)
    ax.set_xticklabels(xticklabels, rotation='vertical')
    plt.savefig(args.plotfile)
