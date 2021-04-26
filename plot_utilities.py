from pyqtgraph import AxisItem
import numpy as np

def timestr_to_seconds(string):
    try:
        start_time = string.split(":")
        start_time = (int(start_time[0]) * 60 + int(start_time[1])) * 60 + float(start_time[2])
    except (ValueError, IndexError) as err:
        print("Error while converting string \"" + string + "\"to seconds")
        print(err)
        print(err.args)
        return None
    return start_time

def second_to_timestr(seconds, fmt):
    H = int(np.floor(seconds) // 3600)
    MM = np.floor(seconds) % 3600
    M = int(MM // 60)
    S = int(MM % 60)
    s = S + seconds - np.floor(seconds)
    return fmt.format(H=H, M=M, S=S, s=s)


class DateAxisItem(AxisItem):
    """
    A tool that provides a date-time aware axis. It is implemented as an
    AxisItem that interpretes positions as unix timestamps (i.e. seconds).
    The labels and the tick positions are dynamically adjusted depending
    on the range.
    It provides a  :meth:`attachToPlotItem` method to add it to a given
    PlotItem
    """
    # Max width in pixels reserved for each label in axis
    _pxLabelWidth = 80

    def __init__(self, *args, **kwargs):
        AxisItem.__init__(self, *args, **kwargs)
        self._oldAxis = None

    def tickValues(self, minVal, maxVal, size):
        """
        Reimplemented from PlotItem to adjust to the range and to force
        the ticks at "round" positions in the context of time units instead of
        rounding in a decimal base
        """

        maxMajSteps = int(size / self._pxLabelWidth)

        dx = maxVal - minVal
        majticks = []
        #TODO optimize
        if dx > 7200:  # 3600s*2 = 2hours
            dt = 1800
            tick = dt * (np.floor(minVal) // dt) + dt
            while tick < maxVal:
                majticks.append(tick)
                tick += dt

        elif dx > 1200:  # 60s*20 = 20 minutes
            dt = 300  # 5 minutes
            tick = dt * (np.floor(minVal) // dt) + dt
            while tick < maxVal:
                majticks.append(tick)
                tick += dt

        elif dx > 120:  # 60s*2 = 2 minutes
            dt = 30  # 30 seconds
            tick = dt * (np.floor(minVal) // dt) + dt
            while tick < maxVal:
                majticks.append(tick)
                tick += dt

        elif dx > 20:  # 20s
            dt = 5  # 5 seconds
            tick = dt * (np.floor(minVal) // dt) + dt
            while tick < maxVal:
                majticks.append(tick)
                tick += dt
        else:  # <20s , use standard implementation from parent
            return AxisItem.tickValues(self, minVal, maxVal, size)

        L = len(majticks)
        if L > maxMajSteps:
            majticks = majticks[::int(np.ceil(float(L) / maxMajSteps))]

        return [(dt, majticks)]

    def tickStrings(self, values, scale, spacing):
        """Reimplemented from PlotItem to adjust to the range"""
        ret = []
        if not values:
            return []

        if spacing >= 60:  # 1 m
            fmt = "{H:02d}:{M:02d}"

        elif spacing >= 1:  # 1s
            fmt = "{H:02d}:{M:02d}:{S:02d}"

        else:
            # less than 2s (show microseconds)
            fmt = "{M:02d}:{s:06.3f}"

        for x in values:
            try:
                ret.append(second_to_timestr(x, fmt))
            except ValueError:  # Windows can't handle dates before 1970
                ret.append('')

        return ret

    def attachToPlotItem(self, plotItem):
        """Add this axis to the given PlotItem
        :param plotItem: (PlotItem)
        """
        self.setParentItem(plotItem)
        viewBox = plotItem.getViewBox()
        self.linkToView(viewBox)
        self._oldAxis = plotItem.axes[self.orientation]['item']
        self._oldAxis.hide()
        plotItem.axes[self.orientation]['item'] = self
        pos = plotItem.axes[self.orientation]['pos']
        plotItem.layout.addItem(self, *pos)
        self.setZValue(-1000)

    def detachFromPlotItem(self):
        """Remove this axis from its attached PlotItem
        (not yet implemented)
        """
        raise NotImplementedError()  # TODO