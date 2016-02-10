import requests
import subprocess
from os import remove

TTS_TYPE_MARY = 1

def send_ssml_str(in_str, out_fname, ip_addr, port, tts_type, lang):
    """sends given ssml string to a tts server and writes the response to a file

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

    returns:
        nothing; the output is written to a file

    raises:
        requests.exceptions.RequestException: the connection failed or the
            server did not return an ok status
    """
    if tts_type == TTS_TYPE_MARY:
        params = {
            'INPUT_TEXT':in_str,
            'INPUT_TYPE':'SSML',
            'OUTPUT_TYPE':'AUDIO',
            'LOCALE':lang,
            'AUDIO':'WAVE_FILE'
            }
        url_suffix = 'process'
    else:
        raise ValueError('tts_type %s not supported' % str(tts_type))

    resp = requests.post('http://%s:%d/%s' % (ip_addr, port, url_suffix),
                         data = params, stream=True)
    with open(out_fname, 'wb') as out_file:
        for chunk in resp.iter_content(8192):
            out_file.write(chunk)
    #do this only after writing output so failure response is written as well
    resp.raise_for_status()


def send_ssml_file(in_fname, out_fname, ip_addr, port, tts_type, lang):
    """sends given ssml file to a tts server and writes the response to a file

    simply reads the file and sends contents using send_ssml_file function above
    (see comments there for details)
    """
    with open(in_fname, 'r') as in_file:
        in_str = ''.join(in_file.readlines())
        send_ssml_str(in_str, out_fname, ip_addr, port, tts_type, lang)


def compute_feature_values(in_fname):
    """runs a praat script to compute a given wav file's feature values

    args:
        in_fname: name of the wav file which should be analyzed

    returns:
        a dictionary containing several feature values, like intensity_mean

    raises:
        subprocess.CalledProcessError: script call did not return with code 0
    """
    out_fname = 'tmp/%s_features.txt' % in_fname.split('.')[0]
    subprocess.check_call(['../Praat.exe', '--run', 'extract_features.praat',
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
