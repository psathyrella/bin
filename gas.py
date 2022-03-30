#!/usr/bin/env python

indata = [
    [12.3,  160882],
    [6.0,  161032],
    [8.3,  161224],
    [5.2, 161344],
    [10.7, 161608],
    [7.8, 161795],
    [9.4, 162042],
    [4.8, 162179],
    [6.4, 162331],
    [12.5, 162617],
    [12.9, 162887],
    [11.7, 163165],
]

mpg_total, total_distance = 0., 0.
print ' miles    gals     mpg'
for idata, (gals, miles) in enumerate(indata):
    if idata > 0:  # can't use the first one, since don't know initial mileage
        distance_travelled = miles - last_miles
        mpg = distance_travelled / float(gals)
        mpg_total += distance_travelled * mpg
        total_distance += distance_travelled
        print '  %3.0f    %5.1f   %5.1f' % (distance_travelled, gals, mpg)

    last_miles = miles

print 'weighted mean: %.1f' % (mpg_total / total_distance)
