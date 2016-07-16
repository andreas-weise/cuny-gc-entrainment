form Adapt
    sentence in_fname
    sentence out_fname
    integer syllable_count
    real target_rate_syll_per_s
    real target_intensity_mean_db
    real target_pitch_mean_hz
endform

sound1 = Read from file... 'in_fname$'
total_duration = Get total duration

if target_rate_syll_per_s > 0
    text_grid = To TextGrid (silences)... 75 0 -35 0.05 0.05 silent sounding
    interval_count = Get number of intervals... 1
    start_point = 0.0
    end_point = 0.0
    silence_duration = 0.0
    interval_label$ = Get label of interval... 1 1
    for interval from 1 to interval_count
        start_point = end_point
        end_point = Get end point... 1 interval
        if interval_label$ == "silent"
            interval_length = end_point - start_point
            silence_duration = silence_duration + interval_length
            interval_label$ = "sounding"
        else
            interval_label$ = "silent"
        endif
    endfor

    select sound1
    speech_duration = total_duration - silence_duration
    ratio = silence_duration / speech_duration
    target_speech_duration = syllable_count / target_rate_syll_per_s
    target_duration = (1 + ratio) * target_speech_duration
    duration_factor = target_duration / total_duration
    sound2 = Change gender... 75 600 1 0 1 duration_factor
    total_duration = Get total duration
endif

if target_pitch_mean_hz > 0
    pitch = To Pitch... 0.0 75 600
    pitch_mean_hz = Get mean... 0.0 0.0 Hertz

    if target_rate_syll_per_s > 0
        select sound2
    else
        select sound1
    endif
    manipulation = To Manipulation... 0.01 75 600
    pitch_tier = Extract pitch tier
    shift = target_pitch_mean_hz - pitch_mean_hz
    Shift frequencies... 0 total_duration shift Hertz
    plus manipulation
    Replace pitch tier
    select manipulation
    sound3 = Get resynthesis (overlap-add)
endif

if target_intensity_mean_db > 0
    Scale intensity... target_intensity_mean_db
endif

Save as WAV file... 'out_fname$'

select sound1
if target_rate_syll_per_s > 0
    plus text_grid
    plus sound2
endif
if target_pitch_mean_hz > 0
    plus pitch
    plus manipulation
    plus pitch_tier
    plus sound3
endif

Remove
