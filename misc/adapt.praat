form Adapt
	sentence in_fname
	sentence out_fname
	integer syllable_count
	real target_rate_syll_per_s
	real target_intensity_mean_db
	real target_pitch_mean_hz
endform

sound = Read from file... 'in_fname$'
pitch = To Pitch... 0.0 75 600
pitch_mean_hz = Get mean... 0.0 0.0 Hertz

select sound
dur = Get total duration
target_dur = syllable_count / target_rate_syll_per_s
dur_factor = target_dur / dur
new_sound = Change gender... 75 600 1 0 1 dur_factor
dur = Get total duration

Scale intensity... target_intensity_mean_db

manipulation = To Manipulation... 0.01 75 600
pitch_tier = Extract pitch tier
shift = target_pitch_mean_hz - pitch_mean_hz
Shift frequencies... 0 dur shift Hertz
plus manipulation
Replace pitch tier
select manipulation
final_sound = Get resynthesis (overlap-add)

Save as WAV file... 'out_fname$'

select sound
plus pitch
plus new_sound
plus manipulation
plus pitch_tier
plus final_sound
Remove