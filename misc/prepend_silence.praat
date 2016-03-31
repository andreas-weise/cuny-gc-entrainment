form PrependSilence
    sentence in_fname
    sentence out_fname
endform

silence = Create Sound from formula... silence 1 0.0 0.05 16000 0
sound = Read from file... 'in_fname$'
plus silence

chain = Concatenate

Save as WAV file... 'out_fname$'

select chain
plus silence
plus sound
Remove

