"""Manipulate fonts in Abaqus/Viewer charts

Carl Osterwisch, November 2013
"""
from abaqus import session

def setFonts(basefont='-*-arial-medium-r-normal-*-*-%d-*-*-p-*-*-*'):
    for chart in session.charts.values():
        chart.legend.textStyle.setValues(
            font=basefont%180)
        for chartAxes in (chart.axes1, chart.axes2):
            for axes in chartAxes:
                axes.titleStyle.setValues(font=basefont%180)
                axes.labelStyle.setValues(font=basefont%140)

    for name, curve in session.curves.items():
        if name.startswith('Test Data'):
            curve.setValues(symbolFrequency=1)

