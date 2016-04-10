import requests
import subprocess
import time
from os import remove
import numpy
import xml.dom.minidom

TTS_TYPE_MARY = 1
MARY_VOICES = ['cmu-bdl-hsmm', 'cmu-rms-hsmm', 'cmu-slt-hsmm']
TTS_TYPE_FESTIVAL = 2
FESTIVAL_VOICES = ['cmu_us_ahw_cg', 'cmu_us_aup_cg', 'cmu_us_awb_cg',
                   'cmu_us_axb_cg', 'cmu_us_bdl_cg', 'cmu_us_clb_cg',
                   'cmu_us_fem_cg', 'cmu_us_gka_cg', 'cmu_us_jmk_cg',
                   'cmu_us_ksp_cg', 'cmu_us_rms_cg', 'cmu_us_rxr_cg',
                   'cmu_us_slt_cg', 'kal_diphone', 'rab_diphone']


def synthesize_str(in_str, out_fname, ip_addr, port, tts_type, lang, input_type,
                   voice=None):
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
        ValueError: the given tts_type is not supported
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

        resp = requests.post('http://%s:%d/%s' % (ip_addr, port, url_suffix),
                             data=params, stream=True)
        with open(out_fname, 'wb') as out_file:
            for chunk in resp.iter_content(8192):
                out_file.write(chunk)
        # do this only after writing output so failure response is written as
        # well in case of errors
        resp.raise_for_status()
    elif tts_type == TTS_TYPE_FESTIVAL:
        args = ['festival_client', '--server', ip_addr, '--port', str(port),
                '--ttw', '--otype', 'wav', '--output', out_fname]
        prolog_fname = None
        if input_type == 'TEXT' and voice:
            # for plain text input voice must be specified in prolog file
            prolog_fname = '../tmp/%s_festival_prolog' % get_fname_suffix()
            with open(prolog_fname, 'wb') as prolog_file:
                prolog_file.write(('(%s)' % voice).encode('utf-8'))
            args.append('--prolog')
            args.append(prolog_fname)
        elif input_type == 'SABLE':
            # for sable input correct tts_mode must be specified
            args.append('--tts_mode')
            args.append('sable')
            # for consistent interface in this function, voice is not assumed to
            # already be specified in given sable string but set here instead;
            # kal_diphone is the only voice that is installed by default
            in_str = in_str.replace('<<<voice>>>',
                                    voice if voice else 'kal_diphone')

        in_fname = '../tmp/%s_festival_input' % get_fname_suffix()
        with open(in_fname, 'wb') as tmp_file:
            tmp_file.write(in_str.encode('utf-8'))
        args.append(in_fname)

        subprocess.check_call(args)
        remove(in_fname)
        if prolog_fname:
            remove(prolog_fname)
    else:
        raise ValueError('tts_type %s not supported' % str(tts_type))


def synthesize_file(in_fname, out_fname, ip_addr, port, tts_type, lang,
                    input_type, voice=None):
    """sends given markup file to a tts server and writes the response to a file

    simply reads the file and sends contents using synthesize_str
    function (see comments there for details)
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
    out_fname = '../tmp/%s_features.txt' % get_fname_suffix()
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
         in_fname], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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


def extract_syllables_text(in_str, ip_addr, port):
    """determines the number of syllables in a given string

    sends the string to marytts for a phoneme computation and determines the
    number of syllables based on the number of vowels in the response (works
    only for 'en_US'

    args:
        in_str: text whose syllable count should be determined
        ip_addr: ip address of the mary tts server
        port: port of the mary tts server

    returns:
        non-negative integer, estimated number of syllables in the given string
    """
    # send text to mary for phoneme computation
    params = {
        'INPUT_TEXT': in_str,
        'INPUT_TYPE': 'TEXT',
        'OUTPUT_TYPE': 'PHONEMES',
        'LOCALE': 'en_US'
    }
    resp = requests.post('http://%s:%d/process' % (ip_addr, port),
                         data=params, stream=True)
    resp_xml = ''
    for chunk in resp.iter_content(8192):
        resp_xml += chunk.decode('utf-8')
    resp.raise_for_status()

    # parse response and count (english) vowels
    vowels = ['A', 'O', 'u', 'i', '{', 'V', 'E', 'I', 'U', '@', 'r=', 'aU',
              'OI', '@U', 'EI', 'AI']
    syll_count = 0
    dom_tree = xml.dom.minidom.parseString(resp_xml)
    collection = dom_tree.documentElement
    tokens = collection.getElementsByTagName('t')
    for token in tokens:
        if token.hasAttribute('ph'):
            ph = token.getAttribute('ph')
            for phone in ph.split():
                if phone in vowels:
                    syll_count += 1

    return syll_count


def synthesize_and_manipulate(in_str, out_fname, speech_rate, intensity, pitch):
    """generates wav file from text with target speech rate, intensity and pitch

    args:
        in_str: text which should be synthesized
        out_fname: file name for the output wav file
        speech_rate: target speech rate in syllables per second
        intensity: target mean intensity in decibel
        pitch: target mean pitch in hertz
    """
    tmp_fname = '../tmp/%s_synthesis.wav' % get_fname_suffix()
    synthesize_str(in_str, tmp_fname, '127.0.0.1', 59125, TTS_TYPE_MARY,
                   'en_US', 'TEXT', 'cmu-bdl-hsmm')

    syll_count = extract_syllables_text(in_str, '127.0.0.1', 59125)
    subprocess.run(['praat', '../misc/adapt.praat',
                    tmp_fname, out_fname, str(syll_count), str(speech_rate),
                    str(intensity), str(pitch)], check=True)
    remove(tmp_fname)


def transcribe_wav(in_fname):
    """generates transcription of a given wav file

    args:
        in_fname: file name of the wav file that should be transcribed

    returns:
        transcription of the wav file
    """
    tmp_fname1 = '../tmp/%s_extended.wav' % get_fname_suffix()
    tmp_fname2 = '../tmp/%s.log' % get_fname_suffix()

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


def get_ssml(in_str, rate='default', pitch='default', volume='default'):
    """returns ssml markup for given string with target prosody

    values for rate, pitch and volume are not checked here, incorrect inputs
    will cause an error; see ssml specification for legal values
    args:
        in_str: plain text string for synthesis
        rate: target speech rate
        pitch: target pitch
        volume: target volume (currently not supported by marytts)

    returns:
        xml of the required ssml markup
    """
    return ('<?xml version="1.0"?>'
            '<speak version="1.0"'
            ' xmlns="http://www.w3.org/2001/10/synthesis"'
            ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
            ' xsi:schemaLocation="http://www.w3.org/2001/10/synthesis'
            ' http://www.w3.org/TR/speech-synthesis/synthesis.xsd"'
            ' xml:lang="en-US">'
            # '.' and '<p>...</p>' are needed for this to work with marytts
            '.<p><prosody pitch="%s" rate="%s" volume="%s">%s</prosody></p>'
            '</speak>'
            % (pitch, rate, volume, in_str))


def get_sable(in_str, rate='default', pitch='default', volume='default'):
    """returns sable markup for given string with target prosody

    args:
        in_str: plain text string for synthesis
        rate: target speech rate
        pitch: target pitch
        volume: target volume (not all festival voices support this)

    returns:
        xml of the required sable markup
    """
    return (
            # no xml version declaration since it causes a warning in festival
            '<SABLE>'
            # voice is only set to placeholder, filled in synthesize_str
            '    <SPEAKER NAME="<<<voice>>>">'
            '        <RATE SPEED="%s">'
            '            <PITCH BASE="%s">'
            '                <VOLUME LEVEL="%s">'
            '                    %s'
            '                </VOLUME>'
            '            </PITCH>'
            '        </RATE>'
            '    </SPEAKER>'
            '</SABLE>'
            % (rate, pitch, volume, in_str))


def load_syllable_count_corpus():
    """loads a small corpus of sentences annotated with syllable counts

    returns:
        list of 2 element lists, index 0 = syllable count, index 1 = text
    """
    corpus = []
    with open('../misc/syllable_count_corpus.txt', 'r') as corpus_file:
        for line in corpus_file.readlines():
            index = line.find(' ')
            corpus.append([int(line[:index]), line[index+1:].replace('\n', '')])
    return corpus


def detect_speech_rate(rate='default', voice='cmu-bdl-hsmm'):
    """determines speech rate for given rate modifier using syllable corpus

    args:
        rate: ssml rate modifier to be used for synthesis
        voice: voice to be used for synthesis

    returns:
        mean speech rate and standard deviation, in syllables per second
    """
    syll_rates = []
    corpus = load_syllable_count_corpus()
    for line in corpus:
        in_str = get_ssml(line[1], rate)
        out_fname = '../tmp/%s_speech_rate.wav' % get_fname_suffix()
        try:
            synthesize_str(in_str, out_fname, '127.0.0.1', 59125, TTS_TYPE_MARY,
                           'en_US', 'SSML', voice)
        except requests.exceptions.HTTPError:
            continue
        duration = float(extract_feature_values(out_fname)['total_duration'])
        syll_rates.append(line[0]/duration)
        remove(out_fname)
    return sum(syll_rates) / len(syll_rates), numpy.std(syll_rates)


def get_fname_suffix():
    """returns a timestamp for file names to make them more or less unique"""
    return time.strftime('%Y%m%d%H%M%S')
