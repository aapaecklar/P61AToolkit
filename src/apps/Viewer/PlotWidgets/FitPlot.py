from PyQt5.Qt import Qt
import pyqtgraph as pg
import numpy as np
import logging

from P61App import P61App
from utils import log_ex_time
from peak_fit_utils import peak_models, background_models


class FitPlot(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None):
        pg.GraphicsLayoutWidget.__init__(self, parent=parent, show=True)
        self.q_app = P61App.instance()
        self.logger = logging.getLogger(str(self.__class__))

        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', 'w')

        self._line_ax = self.addPlot(title="Fit")
        self._line_ax.setLabel('bottom', "Energy", units='eV')
        self._line_ax.setLabel('left', "Intensity", units='counts')
        self._line_ax.showGrid(x=True, y=True)
        self.nextRow()
        self._diff_ax = self.addPlot(title="Difference plot")
        self._diff_ax.setLabel('bottom', "Energy", units='eV')
        self._diff_ax.setLabel('left', "Intensity", units='counts')
        self._diff_ax.showGrid(x=True, y=True)
        self._diff_ax.setXLink(self._line_ax)

        self._diff = None

        self.ci.layout.setRowStretchFactor(0, 4)
        self.ci.layout.setRowStretchFactor(1, 1)

        self.q_app.dataRowsRemoved.connect(self.on_data_rows_removed)
        self.q_app.selectedIndexChanged.connect(self.on_selected_idx_ch)
        self.q_app.peakTracksChanged.connect(self.on_pt_changed)
        self.q_app.peakListChanged.connect(self.on_peaks_changed)
        self.q_app.bckgListChanged.connect(self.on_bckg_changed)
        self.q_app.dataSorted.connect(self.on_data_sorted)

    def on_data_rows_removed(self):
        self.logger.debug('on_data_rows_removed: Handling dataRowsRemoved')
        if self.q_app.data.empty or self.q_app.get_selected_idx() == -1:
            self._line_ax.setTitle('Fit')
            self.clear_axes()
            self._line_ax.addLegend()

    def on_data_sorted(self):
        self.logger.debug('on_data_sorted: Handling dataSorted')
        self.redraw_data()

    def on_selected_idx_ch(self, idx):
        self.logger.debug('on_selected_idx_ch: Handling selectedIndexChanged(%d)' % (idx,))
        self.redraw_data()

    def on_peaks_changed(self, idxs):
        self.logger.debug('on_peaks_changed: Handling peakListChanged(%s)' % (str(idxs),))
        if self.q_app.get_selected_idx() in idxs:
            self.redraw_data()

    def on_bckg_changed(self, idxs):
        self.logger.debug('on_bckg_changed: Handling bckgListChanged(%s)' % (str(idxs),))
        if self.q_app.get_selected_idx() in idxs:
            self.redraw_data()

    def on_pt_changed(self):
        self.logger.debug('on_pt_changed: Handling peakTracksChanged')
        self.redraw_data()

    @log_ex_time()
    def redraw_data(self):
        self._line_ax.setTitle('Fit')
        self.clear_axes()
        self._line_ax.addLegend()
        idx = self.q_app.get_selected_idx()

        if idx != -1:
            self._line_ax.setTitle('Fit: ' + self.q_app.data.loc[idx, 'ScreenName'])
            data = self.q_app.data.loc[idx, ['DataX', 'DataY', 'Color', 'PeakDataList', 'BckgDataList']]

            self._line_ax.plot(1E3 * data['DataX'], data['DataY'],
                               pen=pg.mkPen(color='#000000', style=Qt.DotLine), name='Data')
            xx = data['DataX']
            yy = data['DataY']
            yy_calc = np.zeros(yy.shape)

            if data['BckgDataList'] is not None:
                for bc_md in data['BckgDataList']:
                    yy_bckg = background_models[bc_md.md_name](xx, **bc_md.func_params)
                    yy_calc += yy_bckg
                    self._line_ax.plot(1E3 * xx, yy_bckg,
                                       pen=pg.mkPen(
                                           color=str(hex(next(self.q_app.params['ColorWheel2']))).replace('0x', '#')),
                                       name='[%.f, %.f]: %s' % (
                                       bc_md.md_params['xmin'].n, bc_md.md_params['xmax'].n, bc_md.md_name))

            if data['PeakDataList'] is not None:
                for peak in data['PeakDataList']:
                    yy_peak = peak_models[peak.md_name](xx, **{name: peak.md_params[name].n for name in peak.md_params})
                    yy_calc += yy_peak
                    self._line_ax.plot(1E3 * xx, yy_peak,
                                       pen=pg.mkPen(
                                           color=str(hex(next(self.q_app.params['ColorWheel2']))).replace('0x', '#')),
                                       name='%.01f' % peak.md_params['center'].n)

            self._diff = yy - yy_calc
            self._line_ax.plot(1E3 * xx, yy_calc, pen=pg.mkPen(color='#d62728'), name='Fit')
            self._diff_ax.plot(1E3 * xx, self._diff, pen=pg.mkPen(color='#d62728'))

    def clear_axes(self):
        self._line_ax.clear()
        self._diff_ax.clear()

    def get_axes_xlim(self):
        return tuple(map(lambda x: x * 1E-3, self._line_ax.viewRange()[0]))

    def get_diff(self):
        return self._diff


if __name__ == '__main__':
    from DatasetManager import DatasetManager, DatasetViewer
    import sys

    q_app = P61App(sys.argv)
    app = FitPlot()
    app2 = DatasetManager()
    app3 = DatasetViewer()
    app.show()
    app2.show()
    app3.show()
    sys.exit(q_app.exec_())
