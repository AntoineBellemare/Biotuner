import numpy as np
from biotuner.biotuner_object import compute_biotuner
from biotuner.metrics import ratios2harmsim, compute_subharmonics_2lists, euler
from biotuner.biotuner_utils import rebound_list,butter_bandpass_filter
from biotuner.peaks_extension import harmonic_fit
from biotuner.transitional_harmony import transitional_harmony
from scipy.signal import hilbert
from scipy.stats import zscore
import itertools
import seaborn as sbn
import matplotlib.pyplot as plt
from sklearn.metrics import mutual_info_score
import pywt
from mne.viz import circular_layout
from mne_connectivity.viz import plot_connectivity_circle
import itertools
from PyEMD import EMD
from scipy.signal import hilbert
from biotuner.biotuner_utils import chunk_ts


class harmonic_connectivity(object):
    """
    Class used to compute harmonicity metrics
    between pairs of sensors.
    """

    def __init__(
        self,
        sf=None,
        data=None,
        peaks_function="EMD",
        precision=0.1,
        n_harm=10,
        harm_function="mult",
        min_freq=2,
        max_freq=80,
        n_peaks=5,
    ):
        """
        Parameters
        ----------
        sf: int
            sampling frequency (in Hz)
        data : 2Darray(elec, numDataPoints)
            Electrodes x Time series to analyse.
        peaks_function: str
            Defaults to 'EMD'.
            See compute_biotuner class for details.
        precision: float
            Defaults to 0.1
            precision of the peaks (in Hz)
            When HH1D_max is used, bins are in log scale.
        n_harm: int
            Defaults to 10.
            Set the number of harmonics to compute in harmonic_fit function
        harm_function: str
            {'mult' or 'div'}
            Defaults to 'mult'
            Computes harmonics from iterative multiplication (x, 2x, 3x, ...nx)
            or division (x, x/2, x/3, ...x/n).
        min_freq: float, optional
            Defaults = 2. Minimum frequency (in Hz) to consider for peak extraction.
        max_freq: float, optional
            Defaults = 80. Maximum frequency (in Hz) to consider for peak extraction.
        n_peaks: int, optional
            Default = 5. Number of peaks to extract per frequency band.

        """
        """Initializing data"""
        if type(data) is not None:
            self.data = data
        self.sf = sf
        """Initializing arguments for peak extraction"""
        self.peaks_function = peaks_function
        self.precision = precision
        self.n_harm = n_harm
        self.harm_function = harm_function
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.n_peaks = n_peaks

    def compute_harm_connectivity(self, metric='harmsim', delta_lim=20,
                              save=False, savename='_', graph=True, FREQ_BANDS=None):
        """
        Computes the harmonic connectivity matrix between electrodes.

        Parameters
        ----------
        metric : str, optional
            The metric to use for computing harmonic connectivity. Default is 'harmsim'.
            Possible values are:

            * 'harmsim': computes the harmonic similarity between each pair of peaks from the two electrodes.
            It calculates the ratio between each pair of peaks and computes the mean harmonic similarity.

            * 'euler': computes the Euler's totient function on the concatenated peaks of the two electrodes.
            It provides a measure of the number of positive integers that are relatively prime to the concatenated peaks.

            * 'harm_fit': computes the number of common harmonics between each pair of peaks from the two electrodes.
            It evaluates the harmonic fit between each peak pair and counts the number of common harmonics.

            * 'subharm_tension': computes the tension between subharmonics of two electrodes.
            It evaluates the tension between subharmonics of the two electrodes by comparing the subharmonics and their ratios.

            * 'RRCi': computes the Rhythmic Ratio Coupling with Imaginary Component (RRCi) metric between each pair of
            peaks from the two electrodes, using a bandwidth of 2 Hz and a max_denom of 16. This metric calculates the
            imaginary part of the complex phase differences between two filtered signals, accounting for volume conduction.
            A higher absolute value of the imaginary part indicates stronger phase coupling while being less sensitive
            to volume conduction.

            * 'wPLI_crossfreq': computes the weighted Phase Lag Index (wPLI) for cross-frequency coupling between each pair
            of peaks from the two electrodes. The wPLI measures the phase synchronization between two signals, with a value
            close to 0 indicating no synchronization and a value close to 1 indicating perfect synchronization.

            * 'wPLI_multiband': computes the weighted Phase Lag Index (wPLI) for multiple frequency bands between the two electrodes.
            It calculates wPLI for each frequency band and returns an array of wPLI values for the defined frequency bands.

            * 'MI': computes the Mutual Information (MI) between the instantaneous phases of each pair of peaks from the two electrodes.
            MI is a measure of the dependence between the two signals, with a higher value indicating a stronger relationship.

            * 'MI_spectral': computes the spectral Mutual Information (MI) between the two electrodes for each pair of peaks.
            It evaluates the MI for the concatenated peaks and returns the average MI value for the pairs of peaks.

        delta_lim : int, optional
            The delta limit for the subharmonic tension metric. Default is 20.

        save : bool, optional
            Whether to save the connectivity matrix. Default is False.

        savename : str, optional
            The name to use when saving the connectivity matrix. Default is '_'.

        graph : bool, optional
            Whether to display a heatmap of the connectivity matrix. Default is True.

        Returns
        -------
        conn_matrix : numpy.ndarray
            The harmonic connectivity matrix between electrodes.
        """

        # Initialize biotuner object
        self.metric = metric
        data = self.data
        list_idx = list(range(len(data)))
        pairs = list(itertools.product(list_idx, list_idx))
        harm_conn_matrix = []
        if FREQ_BANDS is None:
            FREQ_BANDS = [
                [2, 3.55],
                [3.55, 7.15],
                [7.15, 14.3],
                [14.3, 28.55],
                [28.55, 49.4],
            ]
        if metric == 'wPLI_multiband':
            harm_conn_matrix = np.zeros((len(FREQ_BANDS), len(data), len(data)))
        for i, pair in enumerate(pairs):
            data1 = data[pair[0]]
            data2 = data[pair[1]]
            #if i % (len(pairs) // 10) == 0:
            percentage_complete = int(i / len(pairs) * 100)
            print(f"{percentage_complete}% complete")
            bt1 = compute_biotuner(self.sf, peaks_function=self.peaks_function,
                                   precision=self.precision, n_harm=self.n_harm)
            bt1.peaks_extraction(data1, min_freq=self.min_freq,
                                 max_freq=self.max_freq, max_harm_freq=150,
                                 n_peaks=self.n_peaks, noverlap=None,
                                 nperseg=None, nfft=None, smooth_fft=1, FREQ_BANDS=FREQ_BANDS)
            list1 = bt1.peaks
            bt2 = compute_biotuner(self.sf, peaks_function=self.peaks_function,
                                   precision=self.precision, n_harm=self.n_harm)
            bt2.peaks_extraction(data2, min_freq=self.min_freq,
                                 max_freq=self.max_freq, max_harm_freq=150,
                                 n_peaks=self.n_peaks, noverlap=None,
                                 nperseg=None, nfft=None, smooth_fft=1, FREQ_BANDS=FREQ_BANDS)

            list2 = bt2.peaks
            if metric == 'subharm_tension':
                common_subs, delta_t, sub_tension_final, harm_temp, pairs_melody = compute_subharmonics_2lists(list1,
                                                                                                 list2,
                                                                                                 self.n_harm,
                                                                                                 delta_lim=delta_lim,
                                                                                                 c=2.1)
                print(sub_tension_final)
                harm_conn_matrix.append(sub_tension_final)
            # compute the harmonic similarity between each pair of peaks from the two electrodes.
            if metric == 'harmsim':
                harm_pairs = list(itertools.product(list1, list2))
                ratios = []
                for p in harm_pairs:
                    if p[0] > p[1]:
                        ratios.append(p[0]/p[1])
                    if p[1] > p[0]:
                        ratios.append(p[1]/p[0])
                ratios = rebound_list(ratios)
                harm_conn_matrix.append(np.mean(ratios2harmsim(ratios)))
            if metric == 'RRCi':
                rrci_values = []
                for peak1 in list1:
                    for peak2 in list2:
                        rrci_value = cross_frequency_rrci(data1, data2, self.sf, peak1, peak2, 2, 16)
                        rrci_values.append(rrci_value)
                harm_conn_matrix.append(np.mean(rrci_values))
            if metric == 'euler':
                list_all = list1 + list2
                list_all = [int(x*10) for x in list_all]
                harm_conn_matrix.append(euler(*list_all))

            # to do
            '''if metric == 'PPC_bicor':
                list_all = list1 + list2
                list_all = [int(x*10) for x in list_all]
                harm_conn_matrix.append(euler(*list_all))'''

            if metric == 'harm_fit':
                harm_pairs = list(itertools.product(list1, list2))
                harm_fit = []
                for p in harm_pairs:
                    a, b, c, d = harmonic_fit(p,
                                              n_harm=self.n_harm,
                                              bounds=0.5,
                                              function="mult",
                                              div_mode="div",
                                              n_common_harms=2)
                    harm_fit.append(len(a))
                harm_conn_matrix.append(np.sum(harm_fit))
            
            if metric == 'wPLI_crossfreq':
                wPLI_values = []
                for peak1 in list1:
                    for peak2 in list2:
                        wPLI_value = wPLI_crossfreq(data1, data2, peak1, peak2, self.sf)
                        wPLI_values.append(wPLI_value)
                harm_conn_matrix.append(np.mean(wPLI_values))

            if metric == 'wPLI_multiband':
                wPLI_values = wPLI_multiband(data1, data2, FREQ_BANDS, self.sf)
                for idx, value in enumerate(wPLI_values):
                    harm_conn_matrix[idx][pair[0]][pair[1]] = value
                
            if metric == 'MI':
                bandwidth = 1
                MI_values = []
                for peak1 in list1:
                    for peak2 in list2:
                        # Filter the original signals using the frequency bands
                        filtered_signal1 = butter_bandpass_filter(data1, peak1 - bandwidth / 2, peak1 + bandwidth / 2, self.sf)
                        filtered_signal2 = butter_bandpass_filter(data2, peak2 - bandwidth / 2, peak2 + bandwidth / 2, self.sf)
                        
                        # Compute the instantaneous phase of each signal using the Hilbert transform
                        analytic_signal1 = hilbert(zscore(filtered_signal1))
                        analytic_signal2 = hilbert(zscore(filtered_signal2))
                        phase1 = np.angle(analytic_signal1)
                        phase2 = np.angle(analytic_signal2)
                        
                        # Compute Mutual Information
                        MI_value = compute_mutual_information(phase1, phase2)
                        MI_values.append(MI_value)

                        harm_conn_matrix.append(np.mean(MI_values))
            
            if metric == 'MI_spectral':
                # Create the pairs of peaks
                peak_pairs = list(itertools.product(list1, list2))

                # Compute the average MI value for the pairs of peaks
                avg_mi = MI_spectral(data1, data2, self.sf, self.min_freq, self.max_freq, self.precision, peak_pairs)
                harm_conn_matrix.append(avg_mi)
            
        if metric == 'wPLI_multiband':
            matrix = harm_conn_matrix
        else:
            matrix = np.empty(shape=(len(data), len(data)))
            for e, p in enumerate(pairs):
                matrix[p[0]][p[1]] = harm_conn_matrix[e]
        #conn_matrix = matrix.astype('float')
        if graph is True:
            sbn.heatmap(matrix)
            plt.show()
        self.conn_matrix = matrix
        return matrix
    
    
    def compute_time_resolved_harm_connectivity(self, sf, nIMFs, metric='harmsim', delta_lim=50):
        """
        Computes the time-resolved harmonic connectivity matrix between electrodes.

        Parameters
        ----------
        data : numpy.ndarray
            Input data with shape (num_electrodes, numDataPoints)
        sf : int
            Sampling frequency
        nIMFs : int
            Number of intrinsic mode functions (IMFs) to consider.
        metric : str, optional
            The metric to use for computing harmonic connectivity. Default is 'harmsim'.
        delta_lim : int, optional
            The delta limit for the subharmonic tension metric. Default is 20.

        Returns
        -------
        connectivity_matrices : numpy.ndarray
            Time-resolved harmonic connectivity matrices with shape (IMFs, numDataPoints, electrodes, electrodes).
        """
        data = self.data
        num_electrodes, numDataPoints = data.shape
        connectivity_matrices = np.zeros((nIMFs, numDataPoints, num_electrodes, num_electrodes))
        harmonicity_cache = {}

        for imf in range(nIMFs):
            for t in range(numDataPoints):
                for i in range(num_electrodes):
                    for j in range(i + 1, num_electrodes):
                        pair_key = (i, j)
                        if pair_key not in harmonicity_cache:
                            time_series1 = data[i, :]
                            time_series2 = data[j, :]
                            harmonicity_cache[pair_key] = EMD_time_resolved_harmonicity(time_series1, time_series2, sf, nIMFs=nIMFs, method=metric)

                        harmonicity = harmonicity_cache[pair_key]
                        connectivity_matrices[imf, t, i, j] = harmonicity[t, imf]
                        connectivity_matrices[imf, t, j, i] = harmonicity[t, imf]

        return connectivity_matrices

    # method for computing inter-electrodes correlations between transitional harmony matrices
    def transitional_connectivity(self, data=None, sf=None, mode='win_overlap', overlap=10, delta_lim=20,
                                graph=False, n_trans_harm=3):
        """
        Compute the transitional connectivity between electrodes using transitional harmony
        and temporal correlation with False Discovery Rate (FDR) correction.

        Parameters
        ----------
        data : numpy.ndarray
            Multichannel EEG data with shape (n_electrodes, n_timepoints).
        sf : float
            Sampling frequency of the EEG data in Hz.
        mode : str, optional, default='win_overlap'
            The mode to compute the transitional harmony. Default is 'win_overlap'.
        overlap : int, optional, default=10
            The percentage of overlap between consecutive windows when computing
            the transitional harmony. Default is 10.
        delta_lim : int, optional, default=20
            The maximum allowed frequency change (delta frequency) between two
            consecutive peaks in Hz. Default is 20.
        graph : bool, optional, default=False
            If True, it will plot the graph of the transitional harmony. Default is False.
        n_trans_harm : int, optional, default=3
            Number of transitional harmonics to compute. Default is 3.

        Returns
        -------
        conn_mat : numpy.ndarray
            Connectivity matrix of shape (n_electrodes, n_electrodes) representing
            the transitional connectivity between electrodes.
        pval_mat : numpy.ndarray
            P-value matrix of shape (n_electrodes, n_electrodes) with FDR-corrected
            p-values for the computed connectivity values.

        Notes
        -----
        This function computes the transitional connectivity between electrodes by
        first calculating the transitional harmony for each electrode and then
        computing the temporal correlation between the transitional harmonies with
        FDR correction for multiple comparisons.
        """
        if sf is None:
            sf = self.sf
        if data is None:
            data = self.data
        trans_subharm_tot = []
        n_electrodes = data.shape[0]
        for elec in range(n_electrodes):
            th = transitional_harmony(sf=self.sf,
                                                data=data[elec, :],
                                                peaks_function=self.peaks_function,
                                                precision=self.precision,
                                                n_harm=self.n_harm,
                                                harm_function="mult",
                                                min_freq=self.min_freq,
                                                max_freq=self.max_freq,
                                                n_peaks=self.n_peaks,
                                                n_trans_harm=n_trans_harm)
            trans_subharm, time_vec_final, pairs_melody = th.compute_trans_harmony(mode='win_overlap', overlap=overlap, delta_lim=delta_lim, graph=graph)
            trans_subharm_tot.append(trans_subharm)
        subharm = np.array(trans_subharm_tot)
        conn_mat, pval_mat = temporal_correlation_fdr(subharm)
        return conn_mat, pval_mat, subharm
    
    def plot_conn_matrix(self, conn_matrix=None, node_names=None):
        if conn_matrix is None:
            conn_matrix = self.conn_matrix
        if node_names is None:
            node_names = range(0, len(conn_matrix), 1)
            node_names = [str(x) for x in node_names]
        fig = plot_connectivity_circle(conn_matrix, node_names=node_names, n_lines=100,
                        fontsize_names=24, show=False, vmin=0.)

    

def wPLI_crossfreq(signal1, signal2, peak1, peak2, sf):
    # Define a band around each peak
    bandwidth = 1  # You can adjust the bandwidth as needed
    
    # Filter the original signals using the frequency bands
    filtered_signal1 = butter_bandpass_filter(signal1, peak1 - bandwidth / 2, peak1 + bandwidth / 2, sf)
    filtered_signal2 = butter_bandpass_filter(signal2, peak2 - bandwidth / 2, peak2 + bandwidth / 2, sf)
    
    # Compute the wPLI between the filtered signals
    n_samples = len(filtered_signal1)
    analytic_signal1 = hilbert(zscore(filtered_signal1))
    analytic_signal2 = hilbert(zscore(filtered_signal2))

    phase_diff = np.angle(analytic_signal1) - np.angle(analytic_signal2)
    wPLI = np.abs(np.mean(np.exp(1j * phase_diff)))

    return wPLI

def wPLI_multiband(signal1, signal2, freq_bands, sf):
    wPLI_values = []
    
    for band in freq_bands:
        lowcut, highcut = band
        
        # Filter the original signals using the frequency bands
        filtered_signal1 = butter_bandpass_filter(signal1, lowcut, highcut, sf)
        filtered_signal2 = butter_bandpass_filter(signal2, lowcut, highcut, sf)
        
        # Compute the wPLI between the filtered signals
        n_samples = len(filtered_signal1)
        analytic_signal1 = hilbert(zscore(filtered_signal1))
        analytic_signal2 = hilbert(zscore(filtered_signal2))

        phase_diff = np.angle(analytic_signal1) - np.angle(analytic_signal2)
        wPLI = np.abs(np.mean(np.exp(1j * phase_diff)))
        print(wPLI)
        wPLI_values.append(wPLI)

    return wPLI_values


def compute_mutual_information(phase1, phase2, num_bins=10):
    # Discretize phase values into bins
    discretized_phase1 = np.digitize(phase1, bins=np.linspace(-np.pi, np.pi, num_bins + 1))
    discretized_phase2 = np.digitize(phase2, bins=np.linspace(-np.pi, np.pi, num_bins + 1))

    # Compute the joint probability distribution of the discretized phase values
    joint_prob, _, _ = np.histogram2d(discretized_phase1, discretized_phase2, bins=num_bins)

    # Normalize the joint probability distribution
    joint_prob = joint_prob / np.sum(joint_prob)

    # Compute Mutual Information
    MI = mutual_info_score(None, None, contingency=joint_prob)

    return MI

def MI_spectral(signal1, signal2, sf, min_freq, max_freq, precision, peak_pairs, wavelet='cmor'):
        # Define the scales for the CWT based on the desired frequency precision
        scales = np.arange(min_freq, max_freq + precision, precision)
        scales = (sf / (2 * np.pi * precision)) * np.divide(1, scales)

        # Compute the Continuous Wavelet Transform of the signals
        cwt_signal1 = pywt.cwt(signal1, scales, wavelet)[0]
        cwt_signal2 = pywt.cwt(signal2, scales, wavelet)[0]

        # Extract the phase values from the CWT coefficients
        phase_signal1 = np.angle(cwt_signal1)
        phase_signal2 = np.angle(cwt_signal2)

        # Compute the Mutual Information between the phase values in the time-frequency domain
        mi_matrix = np.zeros((len(scales), len(scales)))
        for i in range(len(scales)):
            for j in range(len(scales)):
                mi_matrix[i, j] = mutual_info_score(phase_signal1[i, :], phase_signal2[j, :])

        # Extract the MI values corresponding to the pairs of peaks
        mi_values = []
        for pair in peak_pairs:
            scale1 = int((sf / (2 * np.pi * precision)) * np.divide(1, pair[0]))
            scale2 = int((sf / (2 * np.pi * precision)) * np.divide(1, pair[1]))
            mi_values.append(mi_matrix[scale1, scale2])

        # Calculate the average MI value for the pairs of peaks
        avg_mi = np.mean(mi_values)

        return avg_mi
    
from fractions import Fraction
import mne
def cross_frequency_rrci(signal1, signal2, sfreq, freq_peak1, freq_peak2, bandwidth, max_denom):
    freq_band1 = (freq_peak1 - bandwidth/2, freq_peak1 + bandwidth/2)
    freq_band2 = (freq_peak2 - bandwidth/2, freq_peak2 + bandwidth/2)
    
    rhythmic_ratio = compute_rhythmic_ratio(freq_peak1, freq_peak2, max_denom)
    
    rrci = rhythmic_ratio_coupling_imaginary(signal1, signal2, rhythmic_ratio, sfreq, freq_band1, freq_band2)
    return rrci

def compute_rhythmic_ratio(freq1, freq2, max_denom):
    ratio = Fraction(freq1 / freq2).limit_denominator(max_denom)
    return ratio.numerator, ratio.denominator

def rhythmic_ratio_coupling_imaginary(signal1, signal2, rhythmic_ratio, sfreq, freq_band1, freq_band2):
    l_freq1, h_freq1 = freq_band1
    l_freq2, h_freq2 = freq_band2

    # Filter the signals
    filtered_signal1 = mne.filter.filter_data(signal1, sfreq, l_freq1, h_freq1, method='fir', verbose=False)
    filtered_signal2 = mne.filter.filter_data(signal2, sfreq, l_freq2, h_freq2, method='fir', verbose=False)

    # Compute the Hilbert transform
    analytic_signal1 = hilbert(filtered_signal1)
    analytic_signal2 = hilbert(filtered_signal2)

    # Extract instantaneous phases
    phase1 = np.angle(analytic_signal1)
    phase2 = np.angle(analytic_signal2)

    # Calculate the complex phase differences
    n, m = rhythmic_ratio
    phase_diff = n * phase1 - m * phase2

    # Compute the mean of the complex exponential of the phase differences
    mean_exp_phase_diff = np.mean(np.exp(1j * phase_diff))

    # Extract the imaginary part
    imaginary_part = np.imag(mean_exp_phase_diff)

    return np.abs(imaginary_part)


import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from PyEMD import EMD as EMD_eeg
import emd
from biotuner.peaks_extraction import EMD_eeg
from biotuner.metrics import dyad_similarity, compute_subharmonic_tension

def HilbertHuang1D_nopeaks(
    data,
    sf,
    graph=False,
    nIMFs=5,
    min_freq=1,
    max_freq=45,
    precision=0.5,
    bin_spread="log",
    smooth_sigma=None,
    ):
    """
    The Hilbert-Huang transform provides a description of how the energy
    or power within a signal is distributed across frequency.
    The distributions are based on the instantaneous frequency and
    amplitude of a signal.

    Parameters
    ----------
    data : array (numDataPoints,)
        Single time series.
    sf : int
        Sampling frequency.
    graph : bool, default=False
        Defines if a graph is generated.
    nIMFs : int, default=5
        Number of intrinsic mode functions (IMFs) to keep when
        Empirical Mode Decomposition (EMD) is computed.
    min_freq : float, default=1
        Minimum frequency to consider.
    max_freq : float, default=80
        Maximum frequency to consider.
    precision : float, default=0.1
        Value in Hertz corresponding to the minimal step between two
        frequency bins.
    bin_spread : str, default='log'
    
        - 'linear'
        - 'log'
    smooth_sigma : float, default=None
        Sigma value for gaussian smoothing.
    Returns
    -------
    IF : array (numDataPoints,nIMFs)
        instantaneous frequencies associated with each IMF.
    IP : array (numDataPoints,nIMFs)
        instantaneous power associated with each IMF.
    IA : array (numDataPoints,nIMFs)
        instantaneous amplitude associated with each IMF.
    spec : array (nIMFs, nbins)
        Power associated with all bins for each IMF
    bins : array (nIMFs, nbins)
        Frequency bins for each IMF
    """
    IMFs = EMD_eeg(data, method="EMD")
    IMFs = np.moveaxis(IMFs, 0, 1)
    IP, IF, IA = emd.spectra.frequency_transform(IMFs[:, 1:nIMFs + 1], sf, "nht")
    low = min_freq
    high = max_freq
    range_hh = int(high - low)
    steps = int(range_hh / precision)
    bin_size = range_hh / steps
    edges, bins = emd.spectra.define_hist_bins(
        low - (bin_size / 2), high - (bin_size / 2), steps, bin_spread
    )
    # Compute the 1d Hilbert-Huang transform (power over carrier frequency)
    freqs = []
    spec = []
    for IMF in range(len(IF[0])):

        freqs_, spec_ = emd.spectra.hilberthuang(IF[:, IMF], IA[:, IMF], edges)
        if smooth_sigma is not None:
            spec_ = gaussian_filter1d(spec_, smooth_sigma)
        freqs.append(freqs_)
        spec.append(spec_)
    bins_ = []
    for i in range(len(spec)):
        bins_.append(bins)

    if graph is True:
        plt.figure(figsize=(8, 4))
        for plot in range(len(spec)):
            plt.plot(bins_[plot], spec[plot])
        plt.xlim(min_freq, max_freq)
        plt.xscale("log")
        plt.xlabel("Frequency (Hz)")
        plt.title("IA-weighted\nHilbert-Huang Transform")
        plt.legend(["IMF-1", "IMF-2", "IMF-3", "IMF-4", "IMF-5", "IMF-6", "IMF-7"])

    return IF, IP, IA, np.array(spec), np.array(bins_)


def EMD_time_resolved_harmonicity(time_series1, time_series2, sf, nIMFs=5, method='harmsim'):
    """
    Computes the harmonicity between the instantaneous frequencies (IF) for each
    point in time between all pairs of corresponding intrinsic mode functions (IMFs).

    Parameters
    ----------
    time_series1 : array (numDataPoints,)
        First time series.
    time_series2 : array (numDataPoints,)
        Second time series.
    sf : int
        Sampling frequency.
    nIMFs : int, default=5
        Number of intrinsic mode functions (IMFs) to consider.

    Returns
    -------
    harmonicity : array (numDataPoints, nIMFs)
        Harmonicity values for each pair of corresponding IMFs.
    """

    # Compute the Hilbert-Huang transform for each time series
    IF1, _, _, _, _ = HilbertHuang1D_nopeaks(time_series1, sf, nIMFs=nIMFs)
    IF2, _, _, _, _ = HilbertHuang1D_nopeaks(time_series2, sf, nIMFs=nIMFs)
    print(IF1.shape)
    # Compute the harmonicity between the instantaneous frequencies of corresponding IMFs
    harmonicity = np.zeros((IF1.shape[0], nIMFs))

    for i in range(len(IF1)):
        for imf in range(nIMFs):
            if method == 'harmsim':
                try:
                    if IF1[i, imf] > IF2[i, imf]:
                        harmonicity[i, imf] = dyad_similarity(IF1[i, imf] / IF2[i, imf])
                    if IF1[i, imf] < IF2[i, imf]:
                        harmonicity[i, imf] = dyad_similarity(IF2[i, imf] / IF1[i, imf])
                except ZeroDivisionError:
                    harmonicity[i, imf] = 0
            elif method == 'subharm_tension':
                _, _, subharm_tenion, _ = compute_subharmonic_tension([IF1[i, imf], IF2[i, imf]], n_harmonics=10, delta_lim=100, min_notes=2)
                print(subharm_tenion)
                if subharm_tenion != 'NaN':
                    harmonicity[i, imf] = subharm_tenion[0]
                else:
                    pass
    return harmonicity


import numpy as np
import numpy.ma as ma
from scipy.stats import t
from statsmodels.stats.multitest import multipletests

def temporal_correlation_fdr(data):
    """
    Compute the temporal correlation for each pair of electrodes and output a connectivity matrix
    and a matrix of FDR-corrected p-values.

    Args:
    data (array): An array of shape (electrodes, samples) containing the electrode recordings.

    Returns:
    connectivity_matrix (array): A connectivity matrix of shape (electrodes, electrodes) with the temporal correlation for each pair of electrodes.
    fdr_corrected_pvals (array): A matrix of FDR-corrected p-values of shape (electrodes, electrodes).
    """
    if not isinstance(data, np.ndarray):
        data = np.array(data)

    num_electrodes = data.shape[0]

    connectivity_matrix = np.zeros((num_electrodes, num_electrodes))
    pvals_matrix = np.zeros((num_electrodes, num_electrodes))

    for i in range(num_electrodes):
        for j in range(num_electrodes):
            data_i_masked = ma.masked_array(data[i], mask=np.isnan(data[i]))
            data_j_masked = ma.masked_array(data[j], mask=np.isnan(data[j]))

            corr = ma.corrcoef(data_i_masked, data_j_masked, allow_masked=True)[0, 1]
            n = np.sum(~np.isnan(data[i]) & ~np.isnan(data[j]))  # Calculate number of non-NaN data points
            df = n - 2  # Degrees of freedom
            t_val = corr * np.sqrt(df / (1 - corr**2))  # Calculate t-value
            pval = 2 * (1 - t.cdf(abs(t_val), df))  # Calculate two-tailed p-value
            
            connectivity_matrix[i, j], pvals_matrix[i, j] = corr, pval

    pvals = pvals_matrix.flatten()
    fdr_corrected_pvals = multipletests(pvals, method='fdr_bh')[1]
    fdr_corrected_pvals = fdr_corrected_pvals.reshape((num_electrodes, num_electrodes))

    return connectivity_matrix, fdr_corrected_pvals


import numpy as np

'''    def compute_harmonicity_metric_for_IMFs(data, sf, metric='harmsim', delta_lim=20, nIMFs=5, FREQ_BANDS=None):
        # Apply EMD to each channel
        emd_processor = EMD()
        IMFs = [emd_processor(channel)[:nIMFs] for channel in data]

        # Initialize variables
        list_idx = list(range(len(IMFs)))
        pairs = list(itertools.product(list_idx, list_idx))
        harm_conn_matrix = []

        if FREQ_BANDS is None:
            FREQ_BANDS = [
                [2, 3.55],
                [3.55, 7.15],
                [7.15, 14.3],
                [14.3, 28.55],
                [28.55, 49.4],
            ]

        if metric == 'wPLI_multiband':
            harm_conn_matrix = np.zeros((len(FREQ_BANDS), len(IMFs), len(IMFs)))

        # Compute the desired harmonicity metric for each corresponding IMF for each pair of channels
        for pair in pairs:
            imfs1 = IMFs[pair[0]]
            imfs2 = IMFs[pair[1]]

            for i in range(nIMFs):
                for j in range(nIMFs):
                    # Compute the desired harmonicity metric for the pair of IMFs
                    # [Replace this line with the appropriate code to compute the desired harmonicity metric for the pair of IMFs]

        # [Return the appropriate result]'''
    