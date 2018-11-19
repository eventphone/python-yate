#!/usr/bin/python
import os

from yate.ivr import YateIVR


async def main(ivr: YateIVR):
    dirname = os.path.dirname(__file__)
    sndfile = os.path.join(dirname, "test.slin")
    while True:
        dtmf_symbol = await ivr.read_dtmf_symbols(1, timeout_s=30)
        if dtmf_symbol == "*":
            await ivr.silence()
        elif dtmf_symbol == "1":
            await ivr.play_soundfile(sndfile)
        elif dtmf_symbol == "0":
            break

ivr = YateIVR()
ivr.run(main)
