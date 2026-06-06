import os
import ffmpeg
import sys
import glob

outputs_dir = "/home/krish/projects/youtube-shorts-generator-antigravity/backend/outputs"
prop = glob.glob(f"{outputs_dir}/Proposition/*.mp4")[0]
strug = glob.glob(f"{outputs_dir}/Struggle/*.mp4")[0]
res = glob.glob(f"{outputs_dir}/Result/*.mp4")[0]

print(f"Testing concat with:\n{prop}\n{strug}\n{res}")

inputs = []
for clip in [prop, strug, res]:
    in_vid = ffmpeg.input(clip)
    inputs.append(in_vid.video)
    inputs.append(in_vid.audio)

joined = ffmpeg.concat(*inputs, v=1, a=1).node
out = ffmpeg.output(joined[0], joined[1], "/tmp/temp_spliced.mp4", vcodec='libx264', acodec='aac', strict='experimental')
try:
    out.overwrite_output().run(capture_stdout=True, capture_stderr=True)
    print("Success")
except ffmpeg.Error as e:
    print(e.stderr.decode())

