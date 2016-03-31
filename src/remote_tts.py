import requests
import subprocess
import time
from os import remove

import sys
sys.path.insert(0, '../vendor/')
import hyphenate

TTS_TYPE_MARY = 1


def synthesize_str(in_str, out_fname, ip_addr, port, tts_type, lang,
                   input_type, voice=None):
    """sends given string to a tts server and writes response to a file

    args:
        in_str: ssml input as a string
        out_fname: server response is written to this file location; if the
            return status is not ok, this contains additional info
        ip_addr: ip address of the tts server
        port: port of the tts server on which to connect
        tts_type: one of the constants (at the beginning of this module)
            representing supported tts implementations, e.g. MARY TTS
        lang: language system to use, format can depend on tts_type; e.g.
            'en_US' for american english in MARY TTS
        input_type: 'SSML' or 'TEXT'
        voice: name of the voice to use; if none is given, default is used

    returns:
        nothing; the output is written to a file

    raises:
        requests.exceptions.RequestException: the connection failed or the
            server did not return an ok status
    """
    if tts_type == TTS_TYPE_MARY:
        params = {
            'INPUT_TEXT': in_str,
            'INPUT_TYPE': input_type,
            'OUTPUT_TYPE': 'AUDIO',
            'LOCALE': lang,
            'AUDIO': 'WAVE_FILE'
            }
        if voice:
            params['VOICE'] = voice
        url_suffix = 'process'
    else:
        raise ValueError('tts_type %s not supported' % str(tts_type))

    resp = requests.post('http://%s:%d/%s' % (ip_addr, port, url_suffix),
                         data=params, stream=True)
    with open(out_fname, 'wb') as out_file:
        for chunk in resp.iter_content(8192):
            out_file.write(chunk)
    # do this only after writing output so failure response is written as well
    # in case of errors
    resp.raise_for_status()


def synthesize_file(in_fname, out_fname, ip_addr, port, tts_type, lang,
                    input_type, voice=None):
    """sends given markup file to a tts server and writes the response to a file

    simply reads the file and sends contents using synthesize_str
    function above (see comments there for details)
    """
    with open(in_fname, 'r') as in_file:
        in_str = ''.join(in_file.readlines())
        synthesize_str(in_str, out_fname, ip_addr, port, tts_type, lang,
                       input_type, voice)


def extract_feature_values(in_fname):
    """runs a praat script to extract a given wav file's feature values

    args:
        in_fname: name of the wav file which should be analyzed

    returns:
        a dictionary containing several feature values, like intensity_mean

    raises:
        subprocess.CalledProcessError: script call did not return with code 0
    """
    out_fname = '../tmp/%s_features.txt' % time.strftime('%Y%m%d%H%M%S')
    subprocess.check_call(['praat', '../misc/extract_features.praat',
                           in_fname, out_fname])

    # extract comma-separated key value pairs from output file, then delete it
    with open(out_fname, 'r') as out_file:
        lines = out_file.readlines()
        feat_val_dict = {}
        for line in lines:
            key, val = line.replace('\n', '').split(',')
            feat_val_dict[key] = val
    remove(out_fname)

    return feat_val_dict


def extract_syllables_wav(in_fname):
    """runs autobi to extract a given wav file's syllable count and length

    args:
        in_fname: name of the wav file which should be analyzed

    returns:
        estimated number of syllables and their total length in seconds

    raises:
        subprocess.CalledProcessError: autobi call did not return with code 0
        RuntimeError: input file has wrong sample rate (needs to be 16khz)
    """
    # run autobi
    comp_proc = subprocess.run(
        ['java', '-cp', '../vendor/AuToBI.jar',
         'edu.cuny.qc.speech.AuToBI.core.syllabifier.VillingSyllabifier',
         '%s' % in_fname], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, check=True)

    # syllabifier prints to stderr if wrong sample rate is detected
    if comp_proc.stderr:
        raise RuntimeError('wav file does not have 16kHz sample rate')

    # parse stdout for number and length of syllables (ignore 1st/last line)
    syll_count = 0
    syll_len = 0.0
    for line in comp_proc.stdout.split('\n')[1:-1]:
        syll_count += 1
        # lines look like this: 'null [0.47, 1.06] (null)'
        start, end = line.split('[')[1].split(']')[0].split(', ')
        syll_len += float(end) - float(start)

    return syll_count, syll_len


def extract_syllables_text(in_str):
    """runs a hyphenation algorithm to extract syllable count from a given text

    args:
        in_str: text which should be analyzed

    returns:
        estimated number of syllables
    """
    syll_count = 0
    for word in in_str.split():
        syll_count += len(hyphenate.hyphenate_word(word))

    return syll_count


def synthesize_and_manipulate(in_str, out_fname, speech_rate, intensity, pitch):
    tmp_fname = '../tmp/%s_synthesis.wav' % time.strftime('%Y%m%d%H%M%S')
    synthesize_str(in_str, tmp_fname, '127.0.0.1', 59125, TTS_TYPE_MARY,
                   'en_US', 'TEXT', 'cmu-bdl-hsmm')

    syll_count = extract_syllables_text(in_str)
    subprocess.run(['praat', '../misc/adapt.praat',
                    tmp_fname, out_fname, str(syll_count), str(speech_rate),
                    str(intensity), str(pitch)], check=True)
    remove(tmp_fname)


def transcribe_wav(in_fname):
    tmp_fname1 = '../tmp/%s_extended.wav' % time.strftime('%Y%m%d%H%M%S')
    tmp_fname2 = '../tmp/%s.log' % time.strftime('%Y%m%d%H%M%S')

    # prepend some silence so the first bit of speech is not treated as noise
    subprocess.check_call(['praat', '../misc/prepend_silence.praat',
                           in_fname, tmp_fname1])

    # run pocketsphinx (printing to log so only transcript is written to stdout)
    comp_proc = subprocess.run(
        ['pocketsphinx_continuous',
         '-infile', tmp_fname1, '-logfn', tmp_fname2],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    remove(tmp_fname1)
    remove(tmp_fname2)

    return comp_proc.stdout.decode("utf-8").replace('\r\n', '')
