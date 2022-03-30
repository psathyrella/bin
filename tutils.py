import sys
import traceback

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
        print ''.join(10*' '+l for l in elines)
        print '    couldn\'t parse time from \'%s\' (see previous lines)' % instr
        returnval = None
    if debug:
        print '  %s --> %s --> %.2f' % (instr, tstr, returnval)
    return returnval
