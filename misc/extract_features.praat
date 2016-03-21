form ExtractFeatures
    sentence Filename 
    sentence Outfilename
endform

sound = Read from file... 'filename$'

total_duration = Get total duration

intensity = To Intensity... 75 0 yes
intensity_mean = Get mean... 0 0 energy
intensity_mean = round (intensity_mean)
intensity_max = Get maximum... 0 0 Parabolic
intensity_max = round (intensity_max)
intensity_min = Get minimum... 0 0 Parabolic
intensity_min = round (intensity_min)
Remove

select sound

pitch = To Pitch... 0 75 500 
pitch_mean = Get mean... 0 0 Hertz
pitch_mean = round (pitch_mean)
pitch_max = Get maximum... 0 0 Hertz Parabolic
pitch_max = round (pitch_max)
pitch_min = Get minimum... 0 0 Hertz Parabolic
pitch_min = round (pitch_min)
Remove

select sound

total_duration = Get total duration
text_grid = To TextGrid (silences)... 75 0 -25 0.1 0.1 silent sounding
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
            if interval_length > 0.05
                silence_duration = silence_duration + interval_length
            endif
	    interval_label$ = "sounding"
    else
	    interval_label$ = "silent"
	endif
endfor
speech_duration = total_duration - silence_duration

select sound
pitch = To Pitch (cc)... 0 75 15 off 0.03 0.45 0.01 0.35 0.14 600
plus sound
point_process = To PointProcess (cc)

jitter_local = Get jitter (local)... 0 0 0.0001 0.02 1.3

plus sound
shimmer_local = Get shimmer (local)... 0 0 0.0001 0.02 1.3 1.6

plus pitch
plus text_grid
Remove

text$ = "intensity_mean,'intensity_mean''newline$'" 
text$ > 'outfilename$'
text$ = "intensity_max,'intensity_max''newline$'" 
text$ >> 'outfilename$'
text$ = "intensity_min,'intensity_min''newline$'" 
text$ >> 'outfilename$'
text$ = "pitch_mean,'pitch_mean''newline$'"
text$ >> 'outfilename$'
text$ = "pitch_max,'pitch_max''newline$'"
text$ >> 'outfilename$'
text$ = "pitch_min,'pitch_min''newline$'"
text$ >> 'outfilename$'
text$ = "jitter_local,'jitter_local''newline$'"
text$ >> 'outfilename$'
text$ = "shimmer_local,'shimmer_local''newline$'"
text$ >> 'outfilename$'
text$ = "total_duration,'total_duration''newline$'"
text$ >> 'outfilename$'
text$ = "speech_duration,'speech_duration''newline$'"
text$ >> 'outfilename$'
text$ = "silence_duration,'silence_duration''newline$'"
text$ >> 'outfilename$'
