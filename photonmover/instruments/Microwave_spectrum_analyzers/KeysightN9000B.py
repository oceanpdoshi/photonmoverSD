from photonmover.Interfaces.MSA import MSA
from photonmover.Interfaces.Instrument import Instrument

import pyvisa as visa
import time
import numpy as np
import matplotlib.pyplot as plt
import csv


GPIB_ADDRESS = "GPIB0::18::INSTR"


class KeysightN9000B(MSA, Instrument):
    """
    Code for getting data out of the microwave spectrum analyzer
    From Elise.
    """

    def __init__(self):
        super().__init__()
        self.gpib = None

    def initialize(self):
        print('Opening connnection to Keysight MSA')

        rm = visa.ResourceManager()
        try:
            self.gpib = rm.open_resource(GPIB_ADDRESS, timeout=500000)
        except BaseException:
            raise ValueError('Cannot connect to the Keysight MSA')


    def close(self):
        print('Disconnecting Keysight MSA')
        self.gpib.close()

    def set_freq_axis(self, center=None, span=None, start_freq=None, end_freq=None):
        """
        Sets the center and span frequencies, if specified, or
        the start and end frequencies.
        :param center: string with units. Example: '700 MHZ'
        :param span: string with units. Example:  '100 MHZ'
        :param start_freq: initial frequency (string with units)
        :param end_freq: end frequency (string with units)
        :return:
        """

        if center is not None:
            self.gpib.write('FREQ:CENT %s' % center)

        if span is not None:
            self.gpib.write('FREQ:SPAN %s' % span)

        if start_freq is not None:
            self.gpib.write('FREQ:STAR %s' % start_freq)

        if end_freq is not None:
            self.gpib.write('FREQ:STOP %s' % end_freq)

    def set_continuous_acq(self):
        """
        Sets the analyzer to acquire continuous sweeps.
        :return:
        """
        self.gpib.write('INIT:CONT ON')

    def set_single_acq(self):
        """
        Sets the analyzer to acquire single sweep.
        :return:
        """
        self.gpib.write('INIT:CONT OFF')

    def set_acq_bandwidth(self, res_bw, video_bw):
        """
        Sets the bandwidth of the acquisition filters.
        :param res_bw: resolution bandwidth filter  (string with units) ex. '1.0kHz'
        :param video_bw: video bandiwdth filter (string with units)
        :return:
        """

        if res_bw is not None:
            self.gpib.write('BAND %s;' % res_bw)

        if video_bw is not None:
            self.gpib.write('BAND:VID %s;' % video_bw)

    def set_num_points(self, points):
        """
        Sets number of points read in sweep
        """
        self.gpib.write('SWE:POIN %d' % points)

    def instrument_preset(self):
        """
        Sets the instrument to its preset state
        :return:
        """
        self.gpib.write('CONF:CHP')

    def get_sweep_time(self):
        """
        returns instrument sweep time
        """
        return self.gpib.query_ascii_values('SWE:TIME?')[0]


    # def set_reference_level(self, ref_value, ref_pos='TOP'):
    #     """
    #     Doesn't work...need to find the right commands
    #     Sets the reference power level and its position in the screen
    #     :param ref_value: reference level with units. Ex:'-20 dBm'
    #     :param ref_pos: positions reference level at top, center, or bottom of Y scale display. Ex: (TOP, CENT, BOTT)
    #     :return:
    #     """
    #
    #     if ref_value is not None:
    #         # self.gpib.write(':DISP:SPUR:WIND:TRAC:Y:RLEV %s;' % ref_value)
    #         self.gpib.write(':SENS:SPUR:POW:LEV %s;' % ref_value)
    #     # if ref_pos is not None:
    #     #     self.gpib.write(':DISP:DDEM:WIND:Y:RPOS %s' % ref_pos)


    # def set_peak_detection_type(self, type):
    #     """
    #     Sets the peak detection to use.
    #     :param type: 'NRM' for normal, 'POS' for positive peaks, 'NEG' for negative peaks
    #     :return:
    #     """
    #
    #     if type not in ['NRM', 'POS', 'NEG']:
    #         print('Specified detection type not valid. Doing nothing.')
    #         return
    #
    #     self.gpib.write('DET %s;' % type)

    # # def identify_signal(self, move_to_center=False, get_freq=True):
    # #     """
    # #     Tries to identify a signal in the spectrum
    # #     :param move_to_center: If True, it moves the identified signal to the center of the screen
    # #     :param get_freq: if True, it returns the frequency of the identified signal
    # #     :return:
    # #     """
    # #     self.gpib.write('SIGID AUTO;')
    # #
    # #     if move_to_center:
    # #         self.gpib.write('IDCF;')
    # #
    # #     if get_freq:
    # #         return self.gpib.query_ascii_values('IDFREQ?;')
    #
    def get_peak_info(self, trace=1, threshold=-200, excursion=5, sort_order="AMPL"):
        """
        Find the peak of the spectra and returns the frequency and the amplitude in a list
        :param trace to search for peaks [1 to 6]
        :param threshold: threshold for peak [dBm]
        :param excursion: minimum amplitude variation for signal to be identified as peak [dB]
        :param sort_order :"AMPL" or "FREQ"
        :return: [freq, amps] list of peak frequencies, amplitudes
        """
        #Set to ASCII
        self.gpib.write("FORM ASCII")

        peaks = self.gpib.query_ascii_values("CALC:DATA%d:PEAK? %d,%d,%s" %(trace, threshold, excursion, sort_order))
        num_peaks = peaks[0]
        amps = peaks[1]
        freqs = peaks[2]

        return [freqs, amps]
    #
    # def take_sweep(self, num_avg=1):
    #     """
    #     Take sweep
    #     :param num_avg: Number of averages
    #     :return:
    #     """
    #     if num_avg == 1:
    #         self.gpib.write('VAVG OFF;SNGLS;TS;')
    #     else:
    #         self.gpib.write('VAVG %d;VAVG ON;TS' % num_avg)
    #
    def read_data(self, trace_num, filename=None):
        #trace_num - specify which trace (1 to 6) to read

        #Set format to ASCII
        self.gpib.write("FORM ASCII")

        #Initiate a swept spectrum analyzer measurement
        self.gpib.write("INIT:SAN")
        #Read trace
        trace = self.gpib.query_ascii_values("FETC:SAN%d?" %trace_num)

        #Parse into frequency and amplitude arrays
        trace_arr = np.array(trace)
        num_points = int(len(trace)/2)
        #num_points = self.gpib.query("CHP:SWE:POIN?")
        temp = np.reshape(trace_arr, (num_points, 2))
        freqs = temp[:, 0]
        amps = temp[:, 1]

        if filename is not None:
            full_filename = filename + ".csv"
            with open(full_filename, 'w+') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(freqs)
                writer.writerow(amps)

        return [freqs, amps]


if __name__ == '__main__':
    hp = KeysightN9000B()
    hp.initialize()
    # hp.read_data(1, filename='RIN_OEland1038-2mW_BLP-21.4_FDS100-25V-0.76mA_SA-230F5_100kHz-40MHz_RBW10Hz')
    hp.read_data(1, filename='VaryDev1a_FGA21-25V_diamond_electronicNoise_RBW1Hz_SA-230F5_9-10MHz')
    # hp.read_data(1, filename='MSA_diamond-Oeland_BOA700mACW_Dev1a-60V-1254.7nm_manualLock_RBW1Hz_30-40MHz')
    hp.close()

