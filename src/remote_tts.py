import requests
import subprocess
from os import remove

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
            'INPUT_TEXT':in_str,
            'INPUT_TYPE':input_type,
            'OUTPUT_TYPE':'AUDIO',
            'LOCALE':lang,
            'AUDIO':'WAVE_FILE'
            }
        if voice:
            params['VOICE'] = voice
        url_suffix = 'process'
    else:
        raise ValueError('tts_type %s not supported' % str(tts_type))

    resp = requests.post('http://%s:%d/%s' % (ip_addr, port, url_suffix),
                         data = params, stream=True)
    with open(out_fname, 'wb') as out_file:
        for chunk in resp.iter_content(8192):
            out_file.write(chunk)
    #do this only after writing output so failure response is written as well in
    #case of errors
    resp.raise_for_status()


def synthesize_file(in_fname, out_fname, ip_addr, port, tts_type, lang,
                    input_type, voice=None):
    """sends given markup file to a tts server and writes the response to a file

    simply reads the file and sends contents using synthesize_markup_str
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
    out_fname = '%s_features.txt' % in_fname.split('.')[0]
    subprocess.check_call(['../vendor/Praat.exe', '--run',
                           '../misc/extract_features.praat',
                           in_fname, out_fname])

    #extract comma-separated key value pairs from output file, then delete it
    with open(out_fname, 'r') as out_file:
        lines = out_file.readlines()
        feat_val_dict = {}
        for line in lines:
            key, val = line.replace('\n','').split(',')
            feat_val_dict[key] = val
    remove(out_fname)

    return feat_val_dict


def extract_speech_rate(in_fname):
    """runs autobi to extract a given wav file's speech rate

    args:
        in_fname: name of the wav file which should be analyzed

    returns:
        number of syllables and their total length in seconds

    raises:
        subprocess.CalledProcessError: autobi call did not return with code 0
        RuntimeError: input file has wrong sample rate (needs to be 16khz)
    """
    #run autobi (preventing console popup)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    comp_proc = subprocess.run(['java','-cp', '../vendor/AuToBI.jar',
        'edu.cuny.qc.speech.AuToBI.core.syllabifier.VillingSyllabifier',
        '%s'%in_fname], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, check=True, startupinfo=si)

    #syllabifier prints to stderr if wrong sample rate is detected
    if comp_proc.stderr:
        raise RuntimeError('wav file does not have 16kHz sample rate')

    #parse stdout for number and length of syllables (ignore 1st/last line)
    syll_count = 0
    syll_len = 0.0
    for line in comp_proc.stdout.split('\n')[1:-1]:
        syll_count += 1
        #lines look like this: 'null [0.47, 1.06] (null)'
        start, end = line.split('[')[1].split(']')[0].split(', ')
        syll_len += float(end) - float(start)

    return syll_count, syll_len
