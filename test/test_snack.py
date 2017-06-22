from __future__ import division

import math
import random
import unittest
import numpy as np

from sys import platform

# Import user-defined global configuration variables
from conf.userconf import user_default_snack_method

from opensauce.snack import snack_pitch, snack_formants, valid_snack_methods, sformant_names

from opensauce.soundfile import SoundFile

from test.support import TestCase, wav_fns, get_sample_data, get_raw_data

# Figure out appropriate method to use, for calling Snack
if user_default_snack_method is not None:
    if user_default_snack_method in valid_snack_methods:
        if user_default_snack_method == 'exe' and (platform != 'win32' and platform != 'cygwin'):
            raise ValueError("Cannot use 'exe' as Snack calling method, when using non-Windows machine")
        default_snack_method = user_default_snack_method
    else:
        raise ValueError("Invalid Snack calling method. Choices are 'exe', 'python', and 'tcl'")
elif platform == "win32" or platform == "cygwin":
    default_snack_method = 'exe'
elif platform.startswith("linux"):
    default_snack_method = 'tcl'
elif platform == "darwin":
    default_snack_method = 'tcl'
else:
    default_snack_method = 'tcl'

# Shuffle wav filenames, to make sure testing doesn't depend on order
random.shuffle(wav_fns)

class TestSnackPitch(TestCase):

    longMessage = True

    def test_pitch_against_voicesauce_data(self):
        # Test against Snack data generated by VoiceSauce
        # The data was generated on VoiceSauce v1.31 on Windows 7
        for fn in wav_fns:
            f_len = 0.001
            w_len = 0.025
            F0, V = snack_pitch(fn, default_snack_method, frame_length=f_len, window_length=w_len, max_pitch=500, min_pitch=40)

            # The first samples in all of our test data yield 0.
            self.assertTrue(np.allclose(F0[:10], np.zeros(10)))

            # Need ns (number of samples) and sampling rate (Fs) from wav file
            # to compute data length
            sound_file = SoundFile(fn)
            data_len = np.int_(np.floor(sound_file.ns / sound_file.fs / f_len));

            # Following VoiceSauce, pad F0 and V with NaN
            pad_head_F0 = np.full(np.int_(np.floor(w_len / f_len / 2)), np.nan)
            pad_tail_F0 = np.full(data_len - (len(F0) + len(pad_head_F0)), np.nan)
            os_F0 = np.hstack((pad_head_F0, F0, pad_tail_F0))

            pad_head_V = np.full(np.int_(np.floor(w_len / f_len / 2)), np.nan)
            pad_tail_V = np.full(data_len - (len(V) + len(pad_head_V)), np.nan)
            os_V = np.hstack((pad_head_V, V, pad_tail_V))

            # Get VoiceSauce data
            # NB: It doesn't matter which output file we use, the sF0 column is
            # the same in all of them.
            vs_F0 = get_raw_data(fn, 'sF0', 'strF0', 'FMTs', 'estimated')
            vs_V = get_raw_data(fn, 'sV', 'strF0', 'FMTs', 'estimated')

            # Either corresponding entries for OpenSauce and VoiceSauce data
            # have to both be nan, or they need to be "close" enough in
            # floating precision
            # XXX: In later versions of NumPy (v1.10+), you can use NumPy's
            #      allclose() function with the argument equal_nan = True.
            #      But since we can't be sure that the user will have a new
            #      enough version of NumPy, we have to use the complicated
            #      expression below which involves .all()
            self.assertTrue((np.isclose(os_V, vs_V, rtol=1e-05, atol=1e-08) | (np.isnan(os_V) & np.isnan(vs_V))).all())
            if not (np.isclose(os_F0, vs_F0, rtol=1e-05, atol=1e-08) | (np.isnan(os_F0) & np.isnan(vs_F0))).all():
                # If first check fails, try lowering relative tolerance and
                # redoing the check
                idx = np.where(np.isclose(os_F0, vs_F0, rtol=1e-05, atol=1e-08) | (np.isnan(os_F0) & np.isnan(vs_F0)) == False)[0]
                print('\nChecking F0 data using rtol=1e-05, atol=1e-08 in {}:'.format(fn))
                print('Out of {} array entries in F0 snack data, discrepancies in these indices'.format(len(os_F0)))
                for i in idx:
                    print('idx {}, OpenSauce F0 = {}, VoiceSauce F0 = {}'.format(i, os_F0[i], vs_F0[i]))
                print('Reducing relative tolerance to rtol=3e-05 and redoing check:')
                self.assertTrue((np.isclose(os_F0, vs_F0, rtol=3e-05) | (np.isnan(os_F0) & np.isnan(vs_F0))).all())
                print('OK')
            else:
                self.assertTrue((np.isclose(os_F0, vs_F0, rtol=1e-05, atol=1e-08) | (np.isnan(os_F0) & np.isnan(vs_F0))).all())

    def test_pitch_raw(self):
        # Test against previously generated data to make sure nothing has
        # broken and that there are no cross platform or snack version issues.
        # Data was generated by snack 2.2.10 on Manjaro Linux.
        for fn in wav_fns:
            F0, V = snack_pitch(fn, default_snack_method, frame_length=0.001, window_length=0.025, max_pitch=500, min_pitch=40)

            # Check V data
            # Voice is 0 or 1, so (hopefully) no FP rounding issues.
            sample_data = get_sample_data(fn, 'sV', '1ms')
            # Check that all voice data is either 0 or 1
            self.assertTrue(np.all((V == 1) | (V == 0)))
            self.assertTrue(np.all((sample_data == 1) | (sample_data == 0)))
            # Check number of entries is consistent
            self.assertEqual(len(V), len(sample_data))
            # Check actual data values are "close enough",
            # within floating precision
            self.assertTrue(np.allclose(V, sample_data))

            # Check F0 data
            sample_data = get_sample_data(fn, 'sF0', '1ms')
            # Check number of entries is consistent
            self.assertEqual(len(F0), len(sample_data))
            # Check that F0 and sample_data are "close enough" for
            # floating precision
            if not np.allclose(F0, sample_data, rtol=1e-05, atol=1e-08):
                # If first check fails, try lowering relative tolerance and
                # redoing the check
                idx = np.where(np.isclose(F0, sample_data) == False)[0]
                print('\nChecking F0 data using rtol=1e-05, atol=1e-08 in {}:'.format(fn))
                print('Out of {} array entries in F0 snack data, discrepancies in these indices'.format(len(F0)))
                for i in idx:
                    print('idx {}, OpenSauce F0 = {}, sample F0 = {}'.format(i, F0[i], sample_data[i]))
                print('Reducing relative tolerance to rtol=3e-05 and redoing check:')
                self.assertTrue(np.allclose(F0, sample_data, rtol=3e-05))
                print('OK')
            else:
                self.assertTrue(np.allclose(F0, sample_data, rtol=1e-05, atol=1e-08))


class TestSnackFormants(TestCase):

    longMessage = True

    def test_formants_against_voicesauce_data(self):
        # Test against Snack data generated by VoiceSauce
        # The data was generated on VoiceSauce v1.31 on Windows 7

        # XXX: Currently, this test fails if the Snack method used is 'python'
        #      or 'tcl'.  The numbers are extremely different when Snack is
        #      called from the Tcl shell versus the binary executable
        #      snack.exe being used.  No idea why this is the case.
        for fn in wav_fns:
            f_len = 0.001
            w_len = 0.025
            estimates = snack_formants(fn, default_snack_method, frame_length=f_len, window_length=w_len, pre_emphasis=0.96, lpc_order=12)

            # Need ns (number of samples) and sampling rate (Fs) from wav file
            # to compute data length
            sound_file = SoundFile(fn)
            data_len = np.int_(np.floor(sound_file.ns / sound_file.fs / f_len));

            # Following VoiceSauce, pad estimates with NaN
            os_formants = {}
            for n in sformant_names:
                pad_head = np.full(np.int_(np.floor(w_len / f_len / 2)), np.nan)
                pad_tail = np.full(data_len - (len(estimates[n]) + len(pad_head)), np.nan)
                os_formants[n] = np.hstack((pad_head, estimates[n], pad_tail))

            # Get VoiceSauce data
            # NB: It doesn't matter which output file we use, the sF0 column is
            # the same in all of them.
            vs_formants = {}
            for n in sformant_names:
                vs_formants[n] = get_raw_data(fn, n, 'strF0', 'FMTs', 'estimated')

            # Either corresponding entries for OpenSauce and VoiceSauce data
            # have to both be nan, or they need to be "close" enough in
            # floating precision
            # XXX: In later versions of NumPy (v1.10+), you can use NumPy's
            #      allclose() function with the argument equal_nan = True.
            #      But since we can't be sure that the user will have a new
            #      enough version of NumPy, we have to use the complicated
            #      expression below which involves .all()
            tol = 3e-04
            for n in sformant_names:
                self.assertTrue((np.isclose(os_formants[n], vs_formants[n], rtol=tol, atol=1e-08) | (np.isnan(os_formants[n]) & np.isnan(vs_formants[n]))).all())

                if not (np.isclose(os_formants[n], vs_formants[n], rtol=tol, atol=1e-08) | (np.isnan(os_formants[n]) & np.isnan(vs_formants[n]))).all():
                    idx = np.where(np.isclose(os_formants[n], vs_formants[n], rtol=tol, atol=1e-08) | (np.isnan(os_formants[n]) & np.isnan(vs_formants[n])) == False)[0]
                    print('\nChecking {} data in {} using rtol={}, atol=1e-08:'.format(n, fn, tol))
                    print('Out of {} array entries in {} snack data, discrepancies in {} indices'.format(len(os_formants[n]), n, len(idx)))
                    #for i in idx:
                        #print('idx {}, OpenSauce {} = {}, VoiceSauce {} = {}'.format(i, n, os_formants[n][i], n, vs_formants[n][i]))
                else:
                    self.assertTrue((np.isclose(os_formants[n], vs_formants[n], rtol=tol, atol=1e-08) | (np.isnan(os_formants[n]) & np.isnan(vs_formants[n]))).all())

    def test_formants_raw(self):
        # Test against previously generated data to make sure nothing has
        # broken and that there are no cross platform or snack version issues.
        # Data was generated by snack 2.2.10 on Manjaro Linux.
        for fn in wav_fns:
            estimates = snack_formants(fn, default_snack_method, frame_length=0.001, window_length=0.025, pre_emphasis=0.96, lpc_order=12)

            # Get sample data
            sample_data = {}
            for n in sformant_names:
                sample_data[n] = get_sample_data(fn, n, '1ms')

            # Check number of entries is consistent
            for n in sformant_names:
                self.assertEqual(len(estimates[n]), len(sample_data[n]))
            # Check that estimates and sample_data are "close enough" for
            # floating precision
            for n in sformant_names:
                # Increase rtol from 1e-5 to 3e-4 to account for random seed
                # used in Snack formants
                self.assertTrue(np.allclose(estimates[n], sample_data[n], rtol=3e-04, atol=1e-08))
