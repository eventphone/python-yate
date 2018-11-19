#!/usr/bin/python
import os
import asyncio

from yate.ivr import YateIVR


async def main(ivr: YateIVR):
    recording_number = await ivr.read_dtmf_until("#", timeout_s=30)
    if not recording_number.endswith("#"):
        return

    recording_filename = recording_number.rstrip("#") + ".slin"
    recording_path = os.path.join("/tmp/", recording_filename)
    await ivr.tone("busy")
    await asyncio.sleep(0.2)
    await ivr.silence()
    t = await ivr.record_audio(recording_path, time_limit_s=30)
    await ivr.read_dtmf_symbols(1, timeout_s=30)
    if not t.done():
        t.cancel()
        await ivr.stop_recording()

ivr = YateIVR()
ivr.run(main)
