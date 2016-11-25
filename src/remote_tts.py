import requests
import subprocess
from os import remove
from os import getpid
import numpy
import xml.dom.minidom
import threading
import json
import time

TTS_TYPE_MARY = 1
TTS_TYPE_FESTIVAL = 2
MARY_VOICES = ['cmu-bdl-hsmm', 'cmu-rms-hsmm', 'cmu-slt-hsmm']
FESTIVAL_VOICES = ['cmu_us_ahw_cg', 'cmu_us_aup_cg', 'cmu_us_awb_cg',
                   'cmu_us_axb_cg', 'cmu_us_bdl_cg', 'cmu_us_clb_cg',
                   'cmu_us_fem_cg', 'cmu_us_gka_cg', 'cmu_us_jmk_cg',
                   'cmu_us_ksp_cg', 'cmu_us_rms_cg', 'cmu_us_rxr_cg',
                   'cmu_us_slt_cg', 'rab_diphone',   'kal_diphone']
DEFAULT_VOICE_MARY = 'cmu-bdl-hsmm'
DEFAULT_VOICE_FESTIVAL = 'kal_diphone'
INPUT_TYPE_TEXT = 'TEXT'  # value matters, used directly as parameter for mary
INPUT_TYPE_SSML = 'SSML'  # value matters, used directly as parameter for mary
INPUT_TYPE_SABLE = 'SABLE'


def get_unique_fname(name, ftype=None):
    """makes a file name more unique by adding a process id and timestamp to it

    args:
        name: file name including path, excluding file type
        ftype: file type including '.'
    """
    return '%s_%s_%d%s' % (name, time.strftime('%Y%m%d%H%M%S'), getpid(), ftype)


def synthesize(in_str, in_str_is_fname=False, input_type=None, out_fname=None,
               tts_type=None, ip_addr=None, port=None, voice=None):
    """sends given string to a tts server and writes response to a file

    args:
        in_str: plain text or markup string for synthesis or name of a file that
            contains such a string
        in_str_is_fname: whether in_str should be treated as a file name (True)
            or directly as a string to synthesize (False, default)
        input_type: whether the input is plain text (default) or some markup;
            specified by one of the INPUT_TYPE_* constants at the beginning of
            this module
        out_fname: server response is written to this file location; if the
            return status is not ok, this contains additional info; if no name
            is given, a default will be used and returned by this function
        ip_addr: ip address of the tts server, localhost is used if none given
        port: port of the tts server, default for tts is used if none given
        tts_type: tts software to use; specified by one of the TTS_TYPE_*
            constants at the beginning of this module (only those tts are
            supported); marytts is used if none given
        voice: name of the voice to use; default for tts is used if none given

    returns:
        name of the output file, same as out_fname if that was given

    raises:
        requests.exceptions.RequestException: the connection failed or the
            server did not return an ok status
        ValueError: the given tts_type or input_type is not supported
    """
    # if in_str is a file name, read string to synthesize from that file
    if in_str_is_fname:
        with open(in_str, 'r') as in_file:
            in_str = ''.join(in_file.readlines())

    # set defaults for missing parameters
    input_type = input_type if input_type else INPUT_TYPE_TEXT
    tts_type = tts_type if tts_type else TTS_TYPE_MARY
    ip_addr = ip_addr if ip_addr else '127.0.0.1'
    out_fname = out_fname if out_fname \
        else get_unique_fname('../tmp/synthesis', '.wav')
    if tts_type == TTS_TYPE_MARY:
        port = port if port else 59125
        voice = voice if voice else DEFAULT_VOICE_MARY
    elif tts_type == TTS_TYPE_FESTIVAL:
        port = port if port else 1314
        voice = voice if voice else DEFAULT_VOICE_FESTIVAL

    # communicate with tts server in individually appropriate way
    if tts_type == TTS_TYPE_MARY:
        if input_type != INPUT_TYPE_TEXT and input_type != INPUT_TYPE_SSML:
            raise ValueError('given input_type not supported for marytts')

        params = {
            'INPUT_TEXT': in_str,
            'INPUT_TYPE': input_type,
            'OUTPUT_TYPE': 'AUDIO',
            'LOCALE': 'en_US',
            'AUDIO': 'WAVE_FILE',
            'VOICE': voice
        }
        resp = requests.post('http://%s:%d/process' % (ip_addr, port),
                             data=params, stream=True)
        with open(out_fname, 'wb') as out_file:
            for chunk in resp.iter_content(8192):
                out_file.write(chunk)
        # raise exception if http request came back with an error; do this only
        # after writing output so failure response is logged
        # TODO: write to different file (txt, not wav) and include note in msg?
        resp.raise_for_status()
    elif tts_type == TTS_TYPE_FESTIVAL:
        args = ['festival_client', '--server', ip_addr, '--port', str(port),
                '--ttw', '--otype', 'wav', '--output', out_fname]
        prolog_fname = None
        if input_type == INPUT_TYPE_TEXT:
            # for plain text input, voice must be specified in prolog file
            prolog_fname = get_unique_fname('../tmp/festival_prolog', '.wav')
            with open(prolog_fname, 'wb') as prolog_file:
                prolog_file.write(('(%s)' % voice).encode('utf-8'))
            args.append('--prolog')
            args.append(prolog_fname)
        elif input_type == INPUT_TYPE_SABLE:
            # for sable input, tts_mode option must be set
            args.append('--tts_mode')
            args.append('sable')
            # for consistent interface in this function, voice is not assumed to
            # already be specified in given sable string but set here instead
            in_str = in_str.replace('<<<voice>>>', voice)
        else:
            raise ValueError('given input_type not supported for festivaltts')

        in_fname = get_unique_fname('../tmp/festival_input')
        with open(in_fname, 'wb') as tmp_file:
            tmp_file.write(in_str.encode('utf-8'))
        args.append(in_fname)

        subprocess.check_call(args)
        remove(in_fname)
        if prolog_fname:
            remove(prolog_fname)
    else:
        raise ValueError('given tts_type not supported')

    return out_fname


def extract_feature_values(in_fname, extract_intensity=1, extract_pitch=1,
                           extract_durations=1, extract_jitter_shimmer=1):
    """runs a praat script to extract a given wav file's feature values

    args:
        in_fname: name of the wav file which should be analyzed

    returns:
        a dictionary containing several feature values, like intensity_mean

    raises:
        subprocess.CalledProcessError: script call did not return with code 0
    """
    tmp_fname = get_unique_fname('../tmp/features', '.txt')
    subprocess.check_call(['praat', '--run', '../misc/extract_features.praat',
                           in_fname, tmp_fname, str(extract_intensity),
                           str(extract_pitch), str(extract_durations),
                           str(extract_jitter_shimmer)])

    # extract comma-separated key value pairs from output file, then delete it
    with open(tmp_fname, 'r') as out_file:
        lines = out_file.readlines()
        feat_val_dict = {}
        for line in lines:
            key, val = line.replace('\n', '').split(',')
            feat_val_dict[key] = val
    remove(tmp_fname)

    return feat_val_dict


def count_syllables_wav(in_fname):
    """counts number of syllables in a given wav file using autobi

    args:
        in_fname: name of the wav file which should be analyzed

    returns:
        estimated number of syllables

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

    # each output line (except 1st and last) marks one syllable
    syll_count = len(comp_proc.stdout.split('\n')) - 2

    # code to extract syllable lengths as well (results not very reliable)
    # parse stdout for number and length of syllables (ignore 1st/last line)
    # syll_len = 0.0
    # for line in comp_proc.stdout.split('\n')[1:-1]:
    #     syll_count += 1
    #     # lines look like this: 'null [0.47, 1.06] (null)'
    #     start, end = line.split('[')[1].split(']')[0].split(', ')
    #     syll_len += float(end) - float(start)

    return syll_count


def count_syllables_text(in_str, ip_addr=None, port=None):
    """counts number of syllables in a given string

    sends the string to marytts for a phoneme computation and determines the
    number of syllables based on the number of vowels in the response (works
    only for 'en_US')

    args:
        in_str: text whose syllable count should be determined
        ip_addr: ip address of the mary tts server
        port: port of the mary tts server

    returns:
        non-negative integer, estimated number of syllables in the given string

    raises:
        requests.exceptions.RequestException: the connection failed or the
            server did not return an ok status
    """
    ip_addr = ip_addr if ip_addr else '127.0.0.1'
    port = port if port else 59125

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


def synthesize_with_features(in_str, speech_rate=None, intensity=None,
                             pitch=None, in_str_is_fname=False, out_fname=None,
                             tts_type=None, ip_addr=None, port=None, voice=None,
                             speech_rates_dict=None, repeat_until_close=False,
                             syll_count=None):
    """generates wav from plain text with given speech rate, intensity and pitch

    args:
        in_str: text which should be synthesized; either directly plain text or
            the name of a file from which to read plain text
        speech_rate: target mean speech rate in syllables per second (3.0-8.0)
        intensity: target mean intensity in decibel
        pitch: target mean pitch in hertz
        speech_rates_dict: see load_speech_rates_dict(); offered as a parameter
            so it can be loaded once and reused for efficiency; loaded in this
            function if none given
        repeat_until_close: whether to resynthesize until rate and pitch are as
            close to the requested value as possible (only done if neither is
            'default' or None)
        syll_count: number of syllables in the input string to be used if
            repeat_until_close is True; estimated internally if None given
        (for details on other parameters see synthesize())

    returns and raises:
        see synthesize()
    """

    ###############
    # PREPARATION #
    ###############
    # if in_str is a file name, read string to synthesize from that file
    if in_str_is_fname:
        with open(in_str, 'r') as in_file:
            in_str = ''.join(in_file.readlines())
    # store input for later before it is surrounded with markup
    in_str_orig = in_str

    speech_rates_dict = (speech_rates_dict if speech_rates_dict
                         else load_speech_rates_dict())
    pitch = pitch if pitch else 'default'

    # store original target speech rate
    speech_rate_orig = speech_rate
    # adjust target speech rate to be within supported (speech_rates_dict) range
    if speech_rate < 3.0:
        speech_rate = 3.0
    elif speech_rate > 8.0:
        speech_rate = 8.0
    speech_rate = speech_rate if speech_rate else 'default'

    # generate appropriate markup from plain text; only speech rate and pitch
    # are adjusted that way, intensity through praat (this combination is most
    # efficient and accurate)
    if not tts_type or tts_type == TTS_TYPE_MARY:
        input_type = INPUT_TYPE_SSML
        voice = voice if voice else DEFAULT_VOICE_MARY
        rate_modifier = speech_rate if speech_rate == 'default' else \
            speech_rates_dict['mary'][voice][str(round(speech_rate, 1))]
        markup_function = get_ssml
    elif tts_type == TTS_TYPE_FESTIVAL:
        input_type = INPUT_TYPE_SABLE
        voice = voice if voice else DEFAULT_VOICE_MARY
        rate_modifier = speech_rate if speech_rate == 'default' else \
            speech_rates_dict['festival'][voice][round(speech_rate, 1)]
        markup_function = get_sable
    else:
        raise ValueError('given tts_type not supported')
    in_str = markup_function(in_str, rate_modifier, pitch)

    #############
    # SYNTHESIS #
    #############
    # basic synthesis with best estimate of necessary rate modifier
    tmp_fname = synthesize(in_str, False, input_type, None, tts_type,
                           ip_addr, port, voice)

    if repeat_until_close and speech_rate != 'default' and pitch != 'default':
        speech_rate = speech_rate_orig
        # estimate number of syllables if not given
        syll_count = syll_count if syll_count else count_syllables_text(in_str)

        feat_val_dict = extract_feature_values(tmp_fname, 0, 1, 1, 0)
        act_speech_rate = syll_count / float(feat_val_dict['main_duration'])
        act_pitch = float(feat_val_dict['pitch_mean'])
        best_rate = [rate_modifier, abs(speech_rate - act_speech_rate)]
        pct = int(rate_modifier[:-1])
        tgt_pitch = float(pitch[:-2])
        best_pitch = [pitch, abs(tgt_pitch - act_pitch)]
        while True:
            pct += 1 if speech_rate > act_speech_rate else -1
            rate_modifier = '+%d%%' % pct if pct >= 0 else '-%d%%' % pct
            # request pitch as much higher or lower as it was off by before
            pitch = str(float(pitch[:-2]) + tgt_pitch - act_pitch) + 'Hz'
            in_str = markup_function(in_str_orig, rate_modifier, pitch)
            synthesize(in_str, False, input_type, tmp_fname, tts_type,
                       ip_addr, port, voice)
            feat_val_dict = extract_feature_values(tmp_fname, 0, 1, 1, 0)
            act_speech_rate = syll_count / float(feat_val_dict['main_duration'])
            act_pitch = float(feat_val_dict['pitch_mean'])

            if abs(tgt_pitch - act_pitch) < best_pitch[1]:
                best_pitch[0] = pitch
                best_pitch[1] = abs(tgt_pitch - act_pitch)
            if abs(speech_rate - act_speech_rate) > best_rate[1]:
                # rate is as close as possible, now optimize pitch as well
                while True:
                    pitch = str(float(pitch[:-2]) + tgt_pitch - act_pitch) + \
                            'Hz'
                    in_str = markup_function(in_str_orig, best_rate[0], pitch)
                    synthesize(in_str, False, input_type, tmp_fname, tts_type,
                               ip_addr, port, voice)
                    act_pitch = float(extract_feature_values(
                        tmp_fname, 0, 1, 0, 0)['pitch_mean'])
                    if abs(tgt_pitch - act_pitch) > best_pitch[1]:
                        break
                    else:
                        best_pitch[0] = pitch
                        best_pitch[1] = abs(tgt_pitch - act_pitch)
                break
            else:
                best_rate[0] = rate_modifier
                best_rate[1] = abs(speech_rate - act_speech_rate)
        if not tts_type or tts_type == TTS_TYPE_MARY:
            in_str = get_ssml(in_str_orig, best_rate[0], best_pitch[0])
        else:  # tts_type == TTS_TYPE_FESTIVAL
            in_str = get_sable(in_str_orig, best_rate[0], best_pitch[0])
        synthesize(in_str, False, input_type, tmp_fname, tts_type,
                   ip_addr, port, voice)
    out_fname = out_fname if out_fname \
        else get_unique_fname('../tmp/synthesis_final', '.wav')

    adapt_wav(tmp_fname, out_fname, intensity=intensity)
    remove(tmp_fname)
    return out_fname


def adapt_wav(in_fname, out_fname, syll_count=None, speech_rate=None,
              intensity=None, pitch=None):
    """runs praat script to adapt given wav's speech rate, intensity, pitch

    script allows flexibility in terms of which features are adapted, if
    parameter is none, that feature will not be actively adapted (a change in
    another feature can still cause a change in an "unadapted" feature, though)

    args:
        in_fname: input wav file of spoken text
        out_fname: output wav file with adapted features
        syll_count: number of syllables in the input wav file's text
        speech_rate: target mean speech rate in syllables per second
        intensity: target mean intensity in decibel
        pitch: target mean pitch in hertz
    """
    syll_count = syll_count if syll_count else 0
    # in the script, "<= 0" means "do not adapt"
    speech_rate = speech_rate if speech_rate else 0
    intensity = intensity if intensity else 0
    pitch = pitch if pitch else 0

    subprocess.run(['praat', '--run', '../misc/adapt.praat',
                    in_fname, out_fname, str(syll_count), str(speech_rate),
                    str(intensity), str(pitch)], check=True)


def synthesize_alike(in_str, in_fname, in_str_is_fname=False,
                     input_type=None, out_fname=None, tts_type=None,
                     ip_addr=None, port=None, voice=None):
    """synthesizes given string with feature values matching those of given wav

    args:
        in_fname: file name of the wav whose feature values should be matched
        (for details on other parameters see synthesize())

    returns and raises:
        see synthesize()
    """
    syllable_count = 0
    feat_val_dict = {}

    def thread_extract_syllables_text(input_str):
        nonlocal syllable_count
        syllable_count = count_syllables_text(input_str)

    def thread_extract_feature_values(input_fname):
        nonlocal feat_val_dict
        feat_val_dict = extract_feature_values(input_fname)

    thread1 = threading.Thread(target=thread_extract_syllables_text,
                               args=(in_str,))
    thread1.start()
    thread2 = threading.Thread(target=thread_extract_feature_values,
                               args=(in_fname,))
    thread2.start()

    thread1.join()
    thread2.join()

    out_fname = synthesize_with_features(
        in_str, syllable_count / float(feat_val_dict['speech_duration']),
        feat_val_dict['intensity_mean'], feat_val_dict['pitch_mean'],
        in_str_is_fname, out_fname, tts_type, ip_addr, port, voice)
    return out_fname


def transcribe_wav(in_fname):
    """generates transcription of a given wav file

    args:
        in_fname: file name of the wav file that should be transcribed

    returns:
        transcription of the wav file
    """
    tmp_fname1 = get_unique_fname('../tmp/extended', '.wav')
    tmp_fname2 = get_unique_fname('../tmp/transcribe', '.log')

    # prepend some silence (first bit of speech might else be treated as noise)
    subprocess.check_call(['praat', '--run', '../misc/prepend_silence.praat',
                           in_fname, tmp_fname1])

    # run pocketsphinx (printing to log so only transcript is written to stdout)
    comp_proc = subprocess.run(
        ['pocketsphinx_continuous',
         '-infile', tmp_fname1, '-logfn', tmp_fname2],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    remove(tmp_fname1)
    remove(tmp_fname2)

    return comp_proc.stdout.decode("utf-8").replace('\n', '').replace('\r', '')


def get_ssml(in_str, rate='default', pitch='default', volume='default'):
    """returns ssml markup for given string with target prosody

    values for rate, pitch and volume are not checked here, incorrect inputs
    will cause an error; see ssml specification for legal values
    must have same interface as get_sable (assumed in synthesize_with_features)!
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
            # '.' needed for this to work with marytts before 5.2
            '.<prosody pitch="%s" rate="%s" volume="%s">%s</prosody>'
            '</speak>'
            % (pitch, rate, volume, in_str))


def get_sable(in_str, rate='default', pitch='default', volume='default'):
    """returns sable markup for given string with target prosody

    values for rate, pitch and volume are not checked here, incorrect inputs
    will cause an error; see sable specification for legal values
    must have same interface as get_ssml (assumed in synthesize_with_features)!
    args:
        in_str: plain text string for synthesis
        rate: target speech rate
        pitch: target pitch
        volume: target volume (not all festival voices support this)

    returns:
        xml of the required sable markup
    """
    return (  # no xml version declaration since it causes a warning in festival
            '<SABLE>'
            # voice is only set to placeholder, filled in synthesize
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


def load_speech_rates_dict():
    """loads a json file which matches target speech rates to modifiers

    returns:
        dictionary with best modifiers to match target speech rate given a tts,
        voice and target rate; structure: [tts][voice][target_rate]
    """
    return json.load(open('../misc/speech_rates_inverse.json'))


def detect_tts_speech_rate(tts_type, voice, rate_modifier,
                           ip_addr=None, port=None):
    """determines tts average speech rate for given rate modifier

    args:
        tts_type: tts software to use; specified by one of the TTS_TYPE_*
            constants at the beginning of this module (only those tts are
            supported);
        voice: voice to be used for synthesis
        rate_modifier: rate modifier (ssml/sable) to be used for synthesis

    returns:
        mean speech rate and standard deviation, in syllables per second
    """
    syll_rates = []
    corpus = load_syllable_count_corpus()
    # synthesize every line in the corpus, measuring the speech rate for each
    for line in corpus:
        if tts_type == TTS_TYPE_MARY:
            in_str = get_ssml(line[1], rate_modifier)
            input_type = INPUT_TYPE_SSML
        else:
            in_str = get_sable(line[1], rate_modifier)
            input_type = INPUT_TYPE_SABLE
        out_fname = get_unique_fname('../tmp/speech_rate', '.wav')
        try:
            synthesize(in_str, False, input_type, out_fname, tts_type,
                       ip_addr, port, voice)
        except requests.exceptions.HTTPError:
            continue
        # 'main_duration' counts everything except silence at the end
        duration = float(extract_feature_values(out_fname, 0, 0, 1, 0)
                         ['main_duration'])
        syll_rates.append(line[0]/duration)
        remove(out_fname)
    return sum(syll_rates) / len(syll_rates), numpy.std(syll_rates)
