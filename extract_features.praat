form ExtractFeatures
    sentence Filename 
    sentence Outfilename
endform

sound = Read from file... 'filename$'

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

pitch = To Pitch (cc)... 0 75 15 off 0.03 0.45 0.01 0.35 0.14 600
plus sound
point_process = To PointProcess (cc)

jitter_local = Get jitter (local)... 0 0 0.0001 0.02 1.3

plus sound
shimmer_local = Get shimmer (local)... 0 0 0.0001 0.02 1.3 1.6

plus pitch
Remove

writeFileLine ("'outfilename$'", "intensity_mean,'intensity_mean'")
appendFileLine ("'outfilename$'", "intensity_max,'intensity_max'")
appendFileLine ("'outfilename$'", "intensity_min,'intensity_min'")
appendFileLine ("'outfilename$'", "pitch_mean,'pitch_mean'")
appendFileLine ("'outfilename$'", "pitch_max,'pitch_max'")
appendFileLine ("'outfilename$'", "pitch_min,'pitch_min'")
appendFileLine ("'outfilename$'", "jitter_local,'jitter_local'")
appendFileLine ("'outfilename$'", "shimmer_local,'shimmer_local'")
