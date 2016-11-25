import re
import random
import pyaudio
import wave
import sys
from os import remove
import remote_tts
import time
from threading import Thread
import select


def generate_response(in_str):
    """returns a standard phrase or keyword response to a user utterance

    args:
        in_str: user input after pronoun substitution

    returns: system response string based on keywords in user input or unchanged
        input (except for pronouns) if no keyword is found
    """
    if not in_str:
        # give a standard response to empty inputs
        empty_responses = [
            r"i can only help you if you speak to me.",
            r"sorry, i could not hear you. could you repeat that?",
            r"please speak to me so i can help you"
        ]
        choice = random.randint(0, len(empty_responses) - 1)
        out_str = empty_responses[choice]
    elif(in_str.find("how ") == 0 or in_str.find("what ") == 0 or
         in_str.find("where ") == 0 or in_str.find("when ") == 0 or
         in_str.find("why ") == 0 or in_str.find("who ") == 0 or
         in_str.find("which ") == 0 or in_str.find("whose ") == 0):
        # give a standard response to inputs that start with a question word
        question_responses = [
            r"i do not want to answer questions. let us talk about you.",
            r"please do not ask questions. i am more interested in you.",
            r"sorry, i cannot answer any questions. let us talk about you."
        ]
        choice = random.randint(0, len(question_responses) - 1)
        out_str = question_responses[choice]
    elif random.randint(1, 5) == 1:
        # sometimes give a standard response without even considering the input
        standard_responses = [
            r"i see. can you tell me more?",
            r"please tell me more.",
            r"please go on.",
            r"can you elaborate on that?",
            r"please continue"
        ]
        choice = random.randint(0, len(standard_responses) - 1)
        out_str = standard_responses[choice]
    else:
        # otherwise, fully process the input; first make everything upper case
        out_str = in_str.upper()
        # replace occurrences of "I", "YOU" etc. with "you", "i" etc.
        substitutions = [
            (r"\b(I'M|I AM)\b", "you are"),
            (r"[A-Z]\b(AM)\b", " are"),
            (r"\b(I'VE)\b", "you have"),
            (r"\b(I WAS)\b", "you were"),
            (r"\b(I|ME)\b", "you"),
            (r"\b(MY)\b", "your"),
            (r"\b(MYSELF)\b", "yourself"),
            (r"\b(MINE)\b", "yours"),
            (r"\b(YOU'RE|YOU ARE)\b", "i am"),
            (r"\b(YOU'VE)\b", "i have"),
            (r"\b(YOU WERE)\b", "i was"),
            # this does not work well for "YOU" to "me"
            (r"\b(YOU)\b", "i"),
            (r"\b(YOUR)\b", "my"),
            (r"\b(YOURSELF)\b", "myself"),
            (r"\b(YOURS)\b", "mine")
        ]
        for regex, subst_str in substitutions:
            out_str = re.sub(regex, subst_str, out_str)

        # lastly, look for keywords and respond appropriately
        responses = [
            (
                r".*\b(ALWAYS|ALL|(EVERY TIME)|(EACH TIME)|EVERYONE|"
                r"(EVERY PERSON)|EVERYBODY|EVERYWHERE)\b.*",
                [
                    r"can you think of an example?",
                    r"really \1?"
                ]
            ),
            (
                r".*\b(NOONE|NOBODY|NEVER|(NOT EVER)|(NOT ONCE)|NOWHERE)\b.*",
                [
                    r"really \1? i am sure you can think of a counterexample",
                    r"really \1? why do you think that is?"
                ]
            ),
            (
                r".*\byou (LOVE|ADORE|LIKE|MISS|HATE|LOATHE|DETEST|DESPISE|" +
                r"DISLIKE) (.+)",
                [
                    r"tell me what you \1 about \2",
                    r"what else do you \1?"
                ]
            ),
            (
                r".*\bare NOT (.+)",
                [
                    r"why are you not \1?"
                ]
            ),
            (
                r".*\byou (CAN'T|CANNOT) (.+)",
                [
                    r"why can you not \2?",
                    r"would you like to be able to \2?"
                ]
            ),
            (
                r".*\bare (SAD|TIRED|EXHAUSTED|UNHAPPY|DEPRESSED|MISERABLE|" +
                r"HEARTBROKEN|SICK|ILL|HURT|INJURED|NAUSEOUS)\b.*",
                [
                    r"i am sorry to hear you are \1. "
                    r"is that why you want to talk?",
                    r"what made you \1?",
                    r"are you often \1?",
                    r"have you been \1 for long?"
                ]
            ),
            (
                r".*\bare (HAPPY|CHEERFUL|JOYFUL|JOYOUS|CONTENT|DELIGHTED)" +
                r"\b.*",
                [
                    r"i am happy to hear you are \1",
                    r"what made you \1?",
                    r"are you often \1?",
                    r"how long have you been \1?"
                ]
            ),
            (
                r".*\byou (DON'T|(DO NOT)) (.+)",
                [
                    r"why do you not \3?"
                ]
            ),
            (
                r".*\bi (am|DO|DON'T|CAN'T|CANNOT) (.+)",
                [
                    r"why do you think i \1 \2?",
                    r"what makes you say i \1 \2?"
                ]
            ),
            (
                r".*\b(FAMILY|FRIENDS?|RELATIVES?|PARENTS?|FATHER|DAD|MOTHER|"
                r"MOM)\b.*",
                [
                    r"do you like spending time with your \1?",
                    r"do you spend a lot of time with your \1?",
                    r"what do you like to do when you spend time with your \1?",
                    r"does it make you sad if you cannot see your \1 for a "
                    r"while?"
                ]
            ),
            (
                r".*\byour (BOYFRIEND|GIRLFRIEND|FIANCEE?|WIFE|HUSBAND|" +
                r"SPOUSE|PARTNER|KIDS?|CHILD(REN)?|SONS?|DAUGHTERS?)\b.*",
                [
                    r"how does being with your \1 make you feel?",
                    r"how does not being with your \1 make you feel?",
                    r"do you love your \1?"
                ]
            )
        ]

        # start with the input string and loop over all patterns and responses
        for pat, res in responses:
            if re.match(pat, out_str):
                # pattern match was found; randomly choose a response, then stop
                choice = random.randint(0, len(res) - 1)
                out_str = re.sub(pat, res[choice], out_str)
                break
        # note: if no keyword is found out_str will be mostly the same as in_str

    return out_str


def record_audio(out_fname):
    """records audio until timeout occurs or enter is hit by the user

    args:
        out_fname: file name for the wav file of the recording
    """

    # allowing termination of the recording both by user input and by timeout
    # faces the problem that waiting for user input normally blocks the process;
    # here, this was solved by running the recording in a separate thread that
    # communicates with the main process through a shared variable
    recording_stopped = False
    record_timeout_secs = 10

    def thread_rec(wav_fname):
        wav_format = pyaudio.paInt16
        channels = 1
        rate = 16000
        chunk = 1024
        nonlocal recording_stopped, record_timeout_secs

        audio = pyaudio.PyAudio()
        stream = audio.open(format=wav_format, channels=channels, rate=rate,
                            input=True, frames_per_buffer=chunk)
        print('recording (hit enter to stop)...')
        frames = []
        for x in range(0, int(rate / chunk * record_timeout_secs)):
            if recording_stopped:
                break
            else:
                data = stream.read(chunk)
                frames.append(data)
        print('finished recording')

        stream.stop_stream()
        stream.close()
        audio.terminate()

        wav_file = wave.open(wav_fname, 'wb')
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(audio.get_sample_size(wav_format))
        wav_file.setframerate(rate)
        wav_file.writeframes(b''.join(frames))
        wav_file.close()

    thread = Thread(target=thread_rec, args=(out_fname,))
    thread.start()

    # noinspection PyUnusedLocal
    # read 'enter' this way to facilitate timeout
    i, o, e = select.select([sys.stdin], [], [], record_timeout_secs)
    if i:
        # need to flush input, otherwise it triggers the next recording
        sys.stdin.readline()
    # communicate to recording thread that the user stopped the recording
    recording_stopped = True
    # wait for the recording thread to finish writing the wav file
    thread.join()


def play_audio(in_fname):
    """plays audio from a given file

    args:
        in_fname: file name of the audio file to be played
    """
    wf = wave.open(in_fname, 'rb')
    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(), rate=wf.getframerate(),
                    output=True)

    chunk = 1024
    data = wf.readframes(chunk)
    while len(data) > 0:
        stream.write(data)
        data = wf.readframes(chunk)
    if stream.is_active():
        # wait a little at the end, otherwise stop_stream() can cut off audio
        time.sleep(0.2)

    stream.stop_stream()
    stream.close()
    p.terminate()


def main():
    """main function called if the module is run directly and not just imported
    """
    print('this is an interactive dialog system using speech input and output.'
          '\nit is based on the eliza system, which means its '
          'setting is that of rogerian psychotherapy.\nafter each output from '
          'the system, please hit enter to start recording your response and '
          'enter again to stop recording.\nyou might see some error messages '
          'even if the system works without issue in which case you can '
          'ignore them.\nhit enter now to start.')
    sys.stdin.read(1)

    tmp_fname = remote_tts.get_unique_fname('../tmp/%s_eliza_in', '.wav')
    in_str = 'hello, i am a psychotherapist. please tell me about your ' \
             'problems.'

    remote_tts.synthesize(in_str, out_fname=tmp_fname)

    print('me: %s' % in_str)
    play_audio(tmp_fname)
    remove(tmp_fname)

    # loop indefinitely, only stop if the user requests it
    while True:
        in_fname = remote_tts.get_unique_fname('../tmp/%s_eliza_in', '.wav')
        out_fname = remote_tts.get_unique_fname('../tmp/%s_eliza_out', '.wav')

        print('please hit enter and say your response or type "stop" to stop')
        written_input = input()
        if written_input == 'stop':
            break

        record_audio(in_fname)
        in_str = remote_tts.transcribe_wav(in_fname)
        print('you: %s' % in_str)

        out_str = generate_response(in_str).lower()
        print('me: %s' % out_str)
        remote_tts.synthesize_alike(out_str, in_fname, out_fname=out_fname)
        play_audio(out_fname)
        remove(in_fname)
        remove(out_fname)

if __name__ == "__main__":
    main()
