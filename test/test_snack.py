from __future__ import division

import random
import numpy as np

from sys import platform

# Import user-defined global configuration variables
from conf.userconf import user_default_snack_method, user_tcl_shell_cmd

from opensauce.snack import snack_pitch, snack_raw_pitch, snack_formants, snack_raw_formants, valid_snack_methods, sformant_names

from opensauce.soundfile import SoundFile

from test.support import TestCase, wav_fns, get_sample_data, get_raw_data

# Figure out appropriate method to use, for calling Snack
if user_default_snack_method is not None:
    if user_default_snack_method in valid_snack_methods:
        if user_default_snack_method == 'exe' and (platform != 'win32' and platform != 'cygwin'):
            raise ValueError("Cannot use 'exe' as Snack calling method, when using non-Windows machine")
        snack_method = user_default_snack_method
    else:
        raise ValueError("Invalid Snack calling method. Choices are 'exe', 'python', and 'tcl'")
elif platform == "win32" or platform == "cygwin":
    snack_method = 'exe'
elif platform.startswith("linux"):
    snack_method = 'tcl'
elif platform == "darwin":
    snack_method = 'tcl'
else:
    snack_method = 'tcl'

# Figure out Tcl shell command to use
if user_tcl_shell_cmd is not None:
    tcl_cmd = user_tcl_shell_cmd
elif platform == "darwin":
    tcl_cmd = 'tclsh8.4'
else:
    tcl_cmd = 'tclsh'

# Shuffle wav filenames, to make sure testing doesn't depend on order
random.shuffle(wav_fns)

class TestSnackPitch(TestCase):

    longMessage = True

    def test_pitch_against_voicesauce_data(self):
        # Test against Snack data generated by VoiceSauce
        # The data was generated on VoiceSauce v1.31 on Windows 7
        for fn in wav_fns:
            f_len = 1

            # Need ns (number of samples) and sampling rate (Fs) from wav file
            # to compute data length
            sound_file = SoundFile(fn)
            data_len = np.int_(np.floor(sound_file.ns / sound_file.fs / f_len * 1000));

            # Compute OpenSauce Snack F0 and V
            F0_os, V_os = snack_pitch(fn, snack_method, data_len, frame_shift=f_len, window_size=25, max_pitch=500, min_pitch=40, tcl_shell_cmd=tcl_cmd)

            # Get VoiceSauce data
            # NB: It doesn't matter which output file we use, the sF0 column is
            # the same in all of them.
            F0_vs = get_raw_data(fn, 'sF0', 'strF0', 'FMTs', 'estimated')
            V_vs = get_raw_data(fn, 'sV', 'strF0', 'FMTs', 'estimated')

            # Either corresponding entries for OpenSauce and VoiceSauce data
            # have to both be nan, or they need to be "close" enough in
            # floating precision
            # XXX: In later versions of NumPy (v1.10+), you can use NumPy's
            #      allclose() function with the argument equal_nan = True.
            #      But since we can't be sure that the user will have a new
            #      enough version of NumPy, we have to use the complicated
            #      expression below which involves .all()
            self.assertTrue((np.isclose(V_os, V_vs, rtol=1e-05, atol=1e-08) | (np.isnan(V_os) & np.isnan(V_vs))).all())
            if not (np.isclose(F0_os, F0_vs, rtol=1e-05, atol=1e-08) | (np.isnan(F0_os) & np.isnan(F0_vs))).all():
                # If first check fails, try lowering relative tolerance and
                # redoing the check
                idx = np.where(np.isclose(F0_os, F0_vs, rtol=1e-05, atol=1e-08) | (np.isnan(F0_os) & np.isnan(F0_vs)) == False)[0]
                print('\nChecking F0 data using rtol=1e-05, atol=1e-08 in {}:'.format(fn))
                print('Out of {} array entries in F0 snack data, discrepancies in these indices'.format(len(F0_os)))
                for i in idx:
                    print('idx {}, OpenSauce F0 = {}, VoiceSauce F0 = {}'.format(i, F0_os[i], F0_vs[i]))
                print('Reducing relative tolerance to rtol=3e-05 and redoing check:')
                self.assertTrue((np.isclose(F0_os, F0_vs, rtol=3e-05) | (np.isnan(F0_os) & np.isnan(F0_vs))).all())
                print('OK')
            else:
                self.assertTrue((np.isclose(F0_os, F0_vs, rtol=1e-05, atol=1e-08) | (np.isnan(F0_os) & np.isnan(F0_vs))).all())

    def test_pitch_raw(self):
        # Test against previously generated data to make sure nothing has
        # broken and that there are no cross platform or snack version issues.
        # Data was generated by snack 2.2.10 on Manjaro Linux.
        for fn in wav_fns:
            F0_raw, V_raw = snack_raw_pitch(fn, snack_method, frame_shift=1, window_size=25, max_pitch=500, min_pitch=40, tcl_shell_cmd=tcl_cmd)

            # Check V data
            # Voice is 0 or 1, so (hopefully) no FP rounding issues.
            sample_data = get_sample_data(fn, 'snack', 'sV', '1ms')
            # Check that all voice data is either 0 or 1
            self.assertTrue(np.all((V_raw == 1) | (V_raw == 0)))
            self.assertTrue(np.all((sample_data == 1) | (sample_data == 0)))
            # Check number of entries is consistent
            self.assertEqual(len(V_raw), len(sample_data))
            # Check actual data values are "close enough",
            # within floating precision
            self.assertTrue(np.allclose(V_raw, sample_data))

            # Check F0 data
            sample_data = get_sample_data(fn, 'snack', 'sF0', '1ms')
            # Check number of entries is consistent
            self.assertEqual(len(F0_raw), len(sample_data))
            # Check that F0 and sample_data are "close enough" for
            # floating precision
            if not np.allclose(F0_raw, sample_data, rtol=1e-05, atol=1e-08):
                # If first check fails, try lowering relative tolerance and
                # redoing the check
                idx = np.where(np.isclose(F0_raw, sample_data) == False)[0]
                print('\nChecking F0 data using rtol=1e-05, atol=1e-08 in {}:'.format(fn))
                print('Out of {} array entries in F0 snack data, discrepancies in these indices'.format(len(F0_raw)))
                for i in idx:
                    print('idx {}, OpenSauce F0 = {}, sample F0 = {}'.format(i, F0_raw[i], sample_data[i]))
                print('Reducing relative tolerance to rtol=3e-05 and redoing check:')
                self.assertTrue(np.allclose(F0_raw, sample_data, rtol=3e-05))
                print('OK')
            else:
                self.assertTrue(np.allclose(F0_raw, sample_data, rtol=1e-05, atol=1e-08))


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
            f_len = 1
            # Need ns (number of samples) and sampling rate (Fs) from wav file
            # to compute data length
            sound_file = SoundFile(fn)
            data_len = np.int_(np.floor(sound_file.ns / sound_file.fs / f_len * 1000));

            # Compute OpenSauce formant and bandwidth estimates
            formants_os = snack_formants(fn, snack_method, data_len, frame_shift=f_len, window_size=25, pre_emphasis=0.96, lpc_order=12, tcl_shell_cmd=tcl_cmd)

            # Get VoiceSauce data
            # NB: It doesn't matter which output file we use, the sF0 column is
            # the same in all of them.
            formants_vs = {}
            for n in sformant_names:
                formants_vs[n] = get_raw_data(fn, n, 'strF0', 'FMTs', 'estimated')

            # Either corresponding entries for OpenSauce and VoiceSauce data
            # have to both be nan, or they need to be "close" enough in
            # floating precision
            # XXX: In later versions of NumPy (v1.10+), you can use NumPy's
            #      allclose() function with the argument equal_nan = True.
            #      But since we can't be sure that the user will have a new
            #      enough version of NumPy, we have to use the complicated
            #      expression below which involves .all()
            tol = 1e-03
            for n in sformant_names:
                self.assertTrue((np.isclose(formants_os[n], formants_vs[n], rtol=tol, atol=1e-08) | (np.isnan(formants_os[n]) & np.isnan(formants_vs[n]))).all())

                if not (np.isclose(formants_os[n], formants_vs[n], rtol=tol, atol=1e-08) | (np.isnan(formants_os[n]) & np.isnan(formants_vs[n]))).all():
                    idx = np.where(np.isclose(formants_os[n], formants_vs[n], rtol=tol, atol=1e-08) | (np.isnan(formants_os[n]) & np.isnan(formants_vs[n])) == False)[0]
                    print('\nChecking {} data in {} using rtol={}, atol=1e-08:'.format(n, fn, tol))
                    print('Out of {} array entries in {} snack data, discrepancies in {} indices'.format(len(formants_os[n]), n, len(idx)))
                    #for i in idx:
                        #print('idx {}, OpenSauce {} = {}, VoiceSauce {} = {}'.format(i, n, formants_os[n][i], n, formants_vs[n][i]))
                else:
                    self.assertTrue((np.isclose(formants_os[n], formants_vs[n], rtol=tol, atol=1e-08) | (np.isnan(formants_os[n]) & np.isnan(formants_vs[n]))).all())

    def test_formants_raw(self):
        # Test against previously generated data to make sure nothing has
        # broken and that there are no cross platform or snack version issues.
        # Data was generated by snack 2.2.10 on Manjaro Linux.
        for fn in wav_fns:
            estimates_raw = snack_raw_formants(fn, snack_method, frame_shift=1, window_size=25, pre_emphasis=0.96, lpc_order=12, tcl_shell_cmd=tcl_cmd)

            # Get sample data
            sample_data = {}
            for n in sformant_names:
                sample_data[n] = get_sample_data(fn, 'snack', n, '1ms')

            # Check number of entries is consistent
            for n in sformant_names:
                self.assertEqual(len(estimates_raw[n]), len(sample_data[n]))
            # Check that estimates and sample_data are "close enough" for
            # floating precision
            for n in sformant_names:
                # Increase rtol from 1e-5 to 1e-3 to account for random seed
                # used in Snack formants
                self.assertTrue(np.allclose(estimates_raw[n], sample_data[n], rtol=1e-03, atol=1e-08))
