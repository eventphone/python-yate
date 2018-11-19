#!/usr/bin/python
import os

from yate.ivr import YateIVR


async def main(ivr: YateIVR):
    dirname = os.path.dirname(__file__)
    sndfile = os.path.join(dirname, "test.slin")
    await ivr.play_soundfile(sndfile, complete=True)


ivr = YateIVR()
ivr.run(main)
