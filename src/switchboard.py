import remote_tts
import subprocess
import entrainer
from os import remove
from os import rename
from os.path import isfile
import json

"""
This module is used to replace one human speaker in a conversation from the
Switchboard corpus with synthesized speech with given entrainment parameters.
This replacement requires an annotated transcription of the conversation and the
audio of the other speaker as a single channel file.
"""


def add_silence(fname, length_secs):
    """appends given number of seconds of silence to given wav file using sox

    args:
        fname: name of the wav file (will be created if it does not exist yet)
        length_secs: number of seconds of silence to append
    """
    if length_secs <= 0.0:
        return
    if not isfile(fname):
        subprocess.check_call(['rec', '-r', '16k', '-c', '1', '-q', fname,
                               'trim', '0', '0'])
    tmp_fname = fname[:fname.rfind('.')] + 'pad' + fname[fname.rfind('.'):]
    subprocess.check_call(['sox', fname, tmp_fname, 'pad', '0',
                           str(length_secs)])
    remove(fname)
    rename(tmp_fname, fname)


def append_audio(in_fname, out_fname, start, end, up_sample=False):
    """appends given section of one wav file to another

    args:
        in_fname: name of the 1st wav file; part of this is appended to the 2nd
        out_fname: name of the 2nd wav file; part of the 1st is appended to this
        start: beginning of the section in the 1st wav file that is copied
        end: end of the section in the 1st wav file that is copied
        up_sample: whether sample rate of the copied section should be increased
            to 16k (switchboard audio only has 8k initially)
    """
    if not isfile(out_fname):
        subprocess.check_call(['rec', '-r', '16k', '-c', '1', '-q', out_fname,
                               'trim', '0', '0'])
    tmp_fname1 = (in_fname[:in_fname.rfind('.')] + 'cut' +
                  in_fname[in_fname.rfind('.'):])
    tmp_fname2 = (in_fname[:in_fname.rfind('.')] + 'conc' +
                  in_fname[in_fname.rfind('.'):])

    subprocess.check_call(['sox', in_fname, tmp_fname1, 'trim', str(start),
                           '=' + str(end)])
    if up_sample:
        tmp_fname1a = (in_fname[:in_fname.rfind('.')] + 'cut_16k' +
                       in_fname[in_fname.rfind('.'):])
        subprocess.check_call(['sox', tmp_fname1, '-r', '16k', tmp_fname1a])
        remove(tmp_fname1)
        tmp_fname1 = tmp_fname1a
    subprocess.check_call(['sox', out_fname, tmp_fname1, tmp_fname2])
    remove(tmp_fname1)
    remove(out_fname)
    rename(tmp_fname2, out_fname)


def generate_conversation(trans_fname, audio_in_fname, audio_out_fname,
                          entrainer_pitch, entrainer_rate, entrainer_intensity):
    """generates wav file with spliced human and synthesized speech

    args:
        trans_fname: name of the file containing annotated transcription
        audio_in_fname: name of wav file containing human audio
        audio_out_fname: output file name for the wav file to be generated
        entrainer_pitch: instance of entrainer.Entrainer to generate entraining
            values with regard to pitch
        entrainer_rate: instance of entrainer.Entrainer to generate entraining
            values with regard to speech rate
        entrainer_intensity: instance of entrainer.Entrainer to generate
            entraining values with regard to intensity
    """
    # separate channels that get merged at the end
    audio_tmp_hmn_fname = '../tmp/audio_tmp_hmn.wav'
    audio_tmp_syn_fname = '../tmp/audio_tmp_syn.wav'

    speech_rates_dict = remote_tts.load_speech_rates_dict()
    voice = 'cmu-rms-hsmm'

    with open(trans_fname, 'r') as trans_file:
        # arrays to track target values and actual output
        tgt_pitches = []
        act_pitches = []
        tgt_speech_rates = []
        act_speech_rates = []
        tgt_intensities = []
        act_intensities = []

        for line in trans_file.readlines():
            items = line.split(' ')
            # lines begin with 0, 1 or 2 to mark the type of turn
            if items[0] == '0':
                # 0 => silence for both channels
                add_silence(audio_tmp_hmn_fname, float(items[1]))
                add_silence(audio_tmp_syn_fname, float(items[1]))
            elif items[0] == '1':
                # 1 => human speaker's turn; copy section from original audio
                start = float(items[1])
                end = float(items[2])
                dur = end - start
                append_audio(audio_in_fname, audio_tmp_hmn_fname, start, end,
                             True)
                add_silence(audio_tmp_syn_fname, dur)
                # register which values to entrain to in next synthesized turn
                entrainer_pitch.register_input(float(items[4]), dur)
                entrainer_rate.register_input(float(items[5]) / dur, dur)
                entrainer_intensity.register_input(float(items[3]), dur)
            elif items[0] == '2':
                # 2 => synthesized speaker's turn; read text and synthesize
                # get proposed feature values from entrainers
                pitch = entrainer_pitch.propose_output()
                speech_rate = entrainer_rate.propose_output()
                intensity = entrainer_intensity.propose_output()

                # synthesize; keep pitch and rate as close to target as possible
                out_sylls = float(items[1])
                in_str = ' '.join(items[2:])
                fname_tmp = remote_tts.synthesize_with_features(
                    in_str, speech_rate, intensity, str(pitch) + 'Hz',
                    speech_rates_dict=speech_rates_dict,
                    voice=voice, repeat_until_close=True, syll_count=out_sylls
                )

                # determine and track actual output feature values
                feat_val_dict = remote_tts.extract_feature_values(
                    fname_tmp, 1, 1, 1, 0)
                dur = float(feat_val_dict['main_duration'])
                tgt_speech_rates.append('%.2f' % speech_rate)
                act_speech_rates.append('%.2f' % (out_sylls / dur))
                tgt_intensities.append('%.2f' % intensity)
                act_intensities.append('%.2f' %
                                       float(feat_val_dict['intensity_mean']))
                tgt_pitches.append('%.2f' % pitch)
                act_pitches.append('%.2f' % float(feat_val_dict['pitch_mean']))

                add_silence(audio_tmp_hmn_fname, dur)
                append_audio(fname_tmp, audio_tmp_syn_fname, 0, dur)
                remove(fname_tmp)

                # register output with entrainers
                entrainer_pitch.register_output(
                    float(feat_val_dict['pitch_mean']), 1)
                entrainer_rate.register_output(
                    out_sylls / dur, 1)
                entrainer_intensity.register_output(
                    float(feat_val_dict['intensity_mean']), 1)
            else:
                # line does not start with 0, 1 or 2
                print('error!')
                print(line)

    # merge channels and delete intermediate files
    subprocess.check_call(['sox', '-m', audio_tmp_hmn_fname,
                           audio_tmp_syn_fname, audio_out_fname])
    remove(audio_tmp_hmn_fname)
    remove(audio_tmp_syn_fname)

    # return 'log' of target and actual feature values
    return ('p_tgt: ' + ' '.join(tgt_pitches) + '\n' +
            'p_act: ' + ' '.join(act_pitches) + '\n' +
            'r_tgt: ' + ' '.join(tgt_speech_rates) + '\n' +
            'r_act: ' + ' '.join(act_speech_rates) + '\n' +
            'i_tgt: ' + ' '.join(tgt_intensities) + '\n' +
            'i_act: ' + ' '.join(act_intensities) + '\n')


def imitate_conversation(trans_fname, audio_in_fname, audio_out_fname,
                         scale_pitch=True):
    """generates wav file with spliced human and synthesized speech

    unlike in generate_conversation(), synthesis here does not entrainment but
    instead matches the replaced speaker's features as closely as possible

    args:
        trans_fname: name of the file containing annotated transcription
            (annotated for feature values of both speakers)
        audio_in_fname: name of wav file containing human audio
        audio_out_fname: output file name for the wav file to be generated
        scale_pitch: whether to linearly scale pitch from female (75 to 500Hz)
            to male (50 to 300) range or not (output voice is male)
    """
    # separate channels that get merged at the end
    audio_tmp_hmn_fname = '../tmp/audio_tmp_hmn.wav'
    audio_tmp_syn_fname = '../tmp/audio_tmp_syn.wav'

    speech_rates_dict = remote_tts.load_speech_rates_dict()
    voice = 'cmu-rms-hsmm'

    with open(trans_fname, 'r') as trans_file:
        # arrays to track target values and actual output
        tgt_pitches = []
        act_pitches = []
        tgt_speech_rates = []
        act_speech_rates = []
        tgt_intensities = []
        act_intensities = []

        for line in trans_file.readlines():
            items = line.split(' ')
            # lines begin with 0, 1 or 2 to mark the type of turn
            if items[0] == '0':
                # 0 => silence for both channels
                add_silence(audio_tmp_hmn_fname, float(items[1]))
                add_silence(audio_tmp_syn_fname, float(items[1]))
            elif items[0] == '1':
                # 1 => human speaker's turn; copy section from original audio
                start = float(items[1])
                end = float(items[2])
                dur = end - start
                append_audio(audio_in_fname, audio_tmp_hmn_fname, start, end,
                             True)
                add_silence(audio_tmp_syn_fname, dur)
            elif items[0] == '2':
                # 2 => synthesized speaker's turn; read text and features, then
                # synthesize; keep pitch and rate as close to target as possible
                out_sylls = float(items[1])
                intensity = float(items[2])
                pitch = float(items[3])
                if scale_pitch:
                    pitch = 50 + ((pitch - 75) / 425) * 250
                speech_rate = float(items[4])
                in_str = ' '.join(items[5:])
                fname_tmp = remote_tts.synthesize_with_features(
                    in_str, speech_rate, intensity, str(pitch) + 'Hz',
                    speech_rates_dict=speech_rates_dict,
                    voice=voice, repeat_until_close=True, syll_count=out_sylls
                )

                # determine and track actual output feature values
                feat_val_dict = remote_tts.extract_feature_values(
                    fname_tmp, 1, 1, 1, 0)
                dur = float(feat_val_dict['main_duration'])
                tgt_speech_rates.append('%.2f' % speech_rate)
                act_speech_rates.append('%.2f' % (out_sylls / dur))
                tgt_intensities.append('%.2f' % intensity)
                act_intensities.append('%.2f' %
                                       float(feat_val_dict['intensity_mean']))
                tgt_pitches.append('%.2f' % pitch)
                act_pitches.append('%.2f' % float(feat_val_dict['pitch_mean']))

                add_silence(audio_tmp_hmn_fname, dur)
                append_audio(fname_tmp, audio_tmp_syn_fname, 0, dur)
                remove(fname_tmp)
            else:
                # line does not start with 0, 1 or 2
                print('error!')
                print(line)

    # merge channels and delete intermediate files
    subprocess.check_call(['sox', '-m', audio_tmp_hmn_fname,
                           audio_tmp_syn_fname, audio_out_fname])
    remove(audio_tmp_hmn_fname)
    remove(audio_tmp_syn_fname)

    # return 'log' of target and actual feature values
    return ('p_tgt: ' + ' '.join(tgt_pitches) + '\n' +
            'p_act: ' + ' '.join(act_pitches) + '\n' +
            'r_tgt: ' + ' '.join(tgt_speech_rates) + '\n' +
            'r_act: ' + ' '.join(act_speech_rates) + '\n' +
            'i_tgt: ' + ' '.join(tgt_intensities) + '\n' +
            'i_act: ' + ' '.join(act_intensities) + '\n')


def main():
    """generates two conversations for each entrainment configuration"""

    # 'reset' the log file
    log_fname = '../tmp/features.log'
    if isfile(log_fname):
        remove(log_fname)
    audio_in_fname = '../misc/switchboard/human.wav'

    with open('../misc/switchboard/config.json', 'r') as json_file:
        conditions = json.load(json_file)

        for condition in conditions[1:2]:
            for instance in condition:
                for i in [1, 2]:
                    entrainer_pitch = entrainer.Entrainer(
                        instance['pitch']['default'],
                        instance['pitch']['glo_weight'],
                        instance['pitch']['loc_weight'],
                        instance['pitch']['glo_conv'],
                        instance['pitch']['loc_conv'],
                        instance['pitch']['loc_conv'])
                    entrainer_rate = entrainer.Entrainer(
                        instance['rate']['default'],
                        instance['rate']['glo_weight'],
                        instance['rate']['loc_weight'],
                        instance['rate']['glo_conv'],
                        instance['rate']['loc_conv'],
                        instance['rate']['loc_conv'])
                    entrainer_intensity = entrainer.Entrainer(
                        instance['intensity']['default'],
                        instance['intensity']['glo_weight'],
                        instance['intensity']['loc_weight'],
                        instance['intensity']['glo_conv'],
                        instance['intensity']['loc_conv'],
                        instance['intensity']['loc_conv'])

                    audio_out_fname = '../tmp/%s%s.wav' % (instance['id'],
                                                           chr(64 + i))
                    trans_fname = '../misc/switchboard/part%d.text' % i
                    # print('generating file %s' % audio_out_fname)
                    out_str = ('id: ' + instance['id'] + chr(64 + i) + '\n' +
                               'p_cfg: ' + str(entrainer_pitch) + '\n' +
                               'r_cfg: ' + str(entrainer_rate) + '\n' +
                               'i_cfg: ' + str(entrainer_intensity) + '\n')
                    out_str += generate_conversation(
                        trans_fname, audio_in_fname, audio_out_fname,
                        entrainer_pitch, entrainer_rate, entrainer_intensity)
                    with open(log_fname, 'a') as log_file:
                        log_file.write(out_str + '\n')


def main2():
    audio_in_fname = '../misc/switchboard/human.wav'
    for i in [1, 2]:
        audio_out_fname = '../tmp/features_both_%s.wav' % chr(64 + i)
        trans_fname = '../misc/switchboard/part%d_features_both.text' % i
        out_str = imitate_conversation(
            trans_fname, audio_in_fname, audio_out_fname)
        print(out_str)


if __name__ == '__main__':
    main2()
