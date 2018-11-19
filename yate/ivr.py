import asyncio
from enum import Enum
from typing import Optional, Callable

import async_timeout

from yate.asyncio import YateAsync
from yate.protocol import MessageRequest


class ChannelEventType(Enum):
    PLAYBACK_END = 1
    DTMF = 2


class YateIVR(YateAsync):
    def __init__(self):
        super().__init__()
        self._call_ready_future = self.event_loop.create_future()
        self.call_params = {}
        self.dtmf_buffer = ""
        self.dtmf_event = asyncio.Event(loop=self.event_loop)
        self.playback_end_event = asyncio.Event(loop=self.event_loop)
        self._hangup_handlers = []
        # register a listener that takes the call.execute message from yate for the incoming call
        self.register_message_handler("call.execute", self._initial_call_execute_handler, install=False)

    def _initial_call_execute_handler(self, msg):
        self.call_params = msg.params
        self.call_id = msg.params["id"]
        self.event_loop.create_task(self._install_ivr_handlers())
        self.unregister_message_handler("call.execute")
        return True  # Acknowledge that we accepted the call

    def _chan_notify_handler(self, msg):
        if msg.params.get("reason", "") == "eof":
            self.playback_end_event.set()
        return True

    def _chan_dtmf_handler(self, msg):
        self.dtmf_buffer += msg.params["text"]
        self.dtmf_event.set()
        return True

    def _chan_hangup_handler(self, msg):
        for func in self._hangup_handlers:
            func()
        self.main_task.cancel()
        return True

    def register_hangup_handler(self, func: Callable):
        """
        Register a function that should be called when the remote end hung up
        the call before the main task is canceled. Multiple functions
        can be registered in this way. They will be called in the order of their
        registration.

        :param func: A callable with no parameters
        """
        self._hangup_handlers.append(func)

    async def play_soundfile(self, path: str, repeat: bool = False, complete: bool = False) -> bool:
        """
        Play an audio file on this call.

        :param path: absolute path to the audio file location
        :param repeat: True if the audio should automatically repeat after finishing
        :param complete: block coroutine until audio playback has finished, not interrupted by dtmf events
                         cannot be combined with repeat.
        :return: True if the operation was successful, false otherwise
        """
        msg_params = {
            "source": "wave/play/{}".format(path),
            "notify": self.call_id,
        }
        if repeat:
            msg_params["autorepeat"] = "true"
        play_msg = MessageRequest("chan.attach", msg_params)
        self.playback_end_event.clear()
        await self.send_message_async(play_msg)
        if complete:
            await self.playback_end_event.wait()
        return True

    async def record_audio(self, path: str, time_limit_s: float = None) -> Optional[asyncio.Future]:
        """
        Start audio recording on this channel
        :param path: Path of the file where the audio recording should be stored. Use one of
                     yate's supported extensions to indicate the format.
        :param time_limit_s: Optinonal parameter. Seconds to be recorded. If it is present, the recording
                             will be stopped after time_limit_s seconds. In this case, this function returns
                             a future to check if the recording is done and was successful.
        :return: If time_limit_s is present,
        """
        async def _stop_function(ivr):
            await asyncio.sleep(time_limit_s)
            return await ivr.stop_recording()

        await self._send_record_message(path)
        if time_limit_s is not None:
            t = self.event_loop.create_task(_stop_function(self))
            return t

    async def record_audio_wait(self, path: str, time_limit_s: float) -> bool:
        """
        Record the remote end of this call and asynchronously block until
        the time span is over.

        :param path: Path of the file where the audio recording should be stored. Use one of
                     yate's supported extensions to indicate the format.
        :param time_limit_s: Seconds to be recorded.
        :return: True on success, false if yate reported an error.
        """
        await self._send_record_message(path)
        await asyncio.sleep(time_limit_s)
        return await self.stop_recording()

    async def stop_recording(self) -> bool:
        """
        Stop any running recording of the remote end
        :return: True if success, False if yate reported an error.
        """
        await self._send_record_message("-")

    async def _send_record_message(self, path: str) -> bool:
        msg_params = {
            "consumer": "wave/record/{}".format(path),
            "notify": self.call_id,
        }
        play_msg = MessageRequest("chan.attach", msg_params)
        res = await self.send_message_async(play_msg)

    async def read_dtmf_until(self, stop_symbols: str, timeout_s: float = None) -> str:
        """
        Waits for DTMF input and collects it until one of the stop symbols occurs.
        Returns all collected symbols (including the stop symbol)

        :param stop_symbols: A string of symbols. If the first symbol from the string is entered as DTMF,
                              the function return
        :param timeout_s: Optional, if not none, wait for at most timeout_s seconds and returns whatever
                          DTMF symbols where read until then.
        :return: DTMF symbols read.
        """
        local_buf = ""
        try:
            with async_timeout.timeout(timeout_s):
                self.dtmf_buffer = ""
                while True:
                    await self.dtmf_event.wait()
                    self.dtmf_event.clear()
                    for i in range(len(self.dtmf_buffer)):
                        local_buf += self.dtmf_buffer[i]
                        if self.dtmf_buffer[i] in stop_symbols:
                            self.dtmf_buffer = self.dtmf_buffer[i:]
                            return local_buf
                    self.dtmf_buffer = ""
        except asyncio.TimeoutError:
            pass
        return local_buf

    async def read_dtmf_symbols(self, count: int, timeout_s: float = None) -> str:
        """
        Waits for DTMF input and collects it until count symbols occurred.
        Returns all collected symbols.

        :param count: The number of symbols that should be read.
        :param timeout_s: Optional, if not none, wait for at most timeout_s seconds and returns whatever
                          DTMF symbols where read until then.
        :return: DTMF symbols read.
        """
        result = ""
        try:
            with async_timeout.timeout(timeout_s):
                self.dtmf_buffer = ""
                for _ in range(count):
                    await self.dtmf_event.wait()
                    self.dtmf_event.clear()
                    if len(self.dtmf_buffer) >= count:
                        break
            result = self.dtmf_buffer[:count]
            self.dtmf_buffer = self.dtmf_buffer[count:]
            return result
        except asyncio.TimeoutError:
            pass
        return result

    async def silence(self):
        """
        Stop audio playback and just send silence on the channel
        :return: The returned yate message
        """
        return await self.tone("silence")

    async def tone(self, name: str):
        """
        Attach a certain tone as source to our channel
        :return: The returned yate message
        """
        tone_msg = MessageRequest("chan.attach", {"source": "tone/" + name})
        return await self.send_message_async(tone_msg)

    async def wait_channel_event(self, timeout_s: float = None) -> Optional[ChannelEventType]:
        """
        Asynchronous wait function that returns when the next event on the
        channel is triggered. The function returns the kind of event that occurred.

        :param timeout_s: Maximum of seconds to wait for a channel event.
        :return: The type of event that occurred or None if a timeout occurred
        """
        dtmf_waiter = self.event_loop.create_task(self.dtmf_event.wait())
        play_waiter = self.event_loop.create_task(self.playback_end_event.wait())
        done, pending = await asyncio.wait([dtmf_waiter, play_waiter], timeout=timeout_s, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        if dtmf_waiter in done:
            return ChannelEventType.DTMF
        elif play_waiter in done:
            return ChannelEventType.PLAYBACK_END
        else:
            return None

    async def _install_ivr_handlers(self):
        await self.register_message_handler_async("chan.notify", self._chan_notify_handler, 100, "targetid",
                                                  self.call_id)
        await self.register_message_handler_async("chan.dtmf", self._chan_dtmf_handler, 100, "id", self.call_id)
        await self.register_message_handler_async("chan.hangup", self._chan_hangup_handler, 100, "id", self.call_id)
        self._call_ready_future.set_result(None)

    async def _amain_ready(self):
        # wait for yate to pass us our call.execute event and install all default handlers
        await self._call_ready_future
        # well, now we can proceed to applications main

