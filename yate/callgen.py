import argparse
import asyncio
import os
import signal
import logging
from pathlib import Path

from aiohttp import web

from yate.asyncio import YateAsync
from yate.protocol import MessageRequest

soundfile_extensions = [".slin", ".gsm"]



class SoundCallInfo:
    def __init__(self, sndfile, delay):
        self.soundfile = sndfile
        self.delay = delay
        self.answered = False


class YateCallGenerator:
    def __init__(self, port, sounds_directory, bind_global=False):
        logging.info("Initializing application for extmodul yate on port {} and sounds at {}"
                     .format(port, sounds_directory))
        self.shutdown_future = None

        self.active_calls = {}
        self.yate = YateAsync("127.0.0.1", port)
        self.yate.set_termination_handler(self.termination_handler)
        self.sounds_directories = sounds_directory

        self.web_app = web.Application()
        self.web_app.add_routes([web.post("/call", self.web_call_handler)])
        self.app_runner = web.AppRunner(self.web_app)
        self.bind_global = bind_global

    def run(self):
        logging.info("Init YateAsync")
        self.yate.run(self.application_main)

    async def application_main(self, yate):
        logging.info("Starting application main")
        self.shutdown_future = asyncio.get_event_loop().create_future()
        asyncio.get_event_loop().add_signal_handler(signal.SIGINT, self.shutdown)

        if not await self.yate.register_watch_handler_async("call.answered", self._call_answered_handler):
            logging.error("Cannot watch call.answered.")
            return
        if not await self.yate.register_watch_handler_async("chan.notify", self._chan_notify_handler):
            logging.error("Cannot watch chan.notify.")
            return
        if not await self.yate.register_watch_handler_async("chan.hangup", self._chan_hangup_handler):
            logging.error("Cannot watch chan.hangup")
            return
        logging.info("Yate ready. Starting webserver.")

        # fire up http server
        bind = None if self.bind_global else "localhost"
        await self.app_runner.setup()
        site = web.TCPSite(self.app_runner, bind, 8080)
        await site.start()
        logging.info("Webserver ready. Waiting for requests {}.".format("globally" if self.bind_global else "locally"))

        # We wait to be signaled for shutdown.
        await self.shutdown_future
        logging.info("Shutting down...")
        await self.app_runner.cleanup()

    def shutdown(self):
        self.shutdown_future.set_result(True)

    @staticmethod
    def termination_handler():
        logging.info("Yate has closed the connection. Terminating application.")
        os._exit(1)


    async def web_call_handler(self, request):
        logging.debug("TRACE: Request handler begin")
        params = await request.post()

        soundfile = params.get("soundfile")
        delay = params.get("delay")
        target = params.get("target")
        caller = params.get("caller", "")
        callername = params.get("callername", "")
        max_ringtime = params.get("max_ringtime")

        if any((soundfile is None, delay is None, target is None)):
            return web.Response(status=400, text="Provide at least <soundfile>, <delay> and <target>")
        if not delay.isnumeric():
            return web.Response(status=400, text="<delay> needs to be numeric")
        delay = int(delay)
        if max_ringtime is not None:
            if not max_ringtime.isnumeric():
                return web.Response(status=400, text="<max_ringtime> needs to be numeric")
            else:
                max_ringtime = int(max_ringtime)

        sound_path = self.find_soundfile(soundfile)
        if sound_path is None:
            return web.Response(status=404, text="Soundfile {} not found".format(soundfile))

        call_execute_message = MessageRequest("call.execute", {
            "callto": "dumb/",
            "target": target,
            "autoanswer": "yes",
            "caller": caller,
            "callername": callername,
        })
        result = await self.yate.send_message_async(call_execute_message)
        if not result.processed:
            return web.Response(status=404, text="Call.execute failed. Invalid target?")

        id = result.params["id"]
        call_info = SoundCallInfo(sound_path, delay)
        self.active_calls[id] = call_info
        if max_ringtime is not None:
            asyncio.get_event_loop().call_later(max_ringtime, self.drop_call_if_not_answered, id)

        return web.Response(text="OK :-)")

    def _call_answered_handler(self, msg):
        peer = msg.params["peerid"]
        if peer in self.active_calls:
            call_info = self.active_calls[peer]
            call_info.answered = True
            asyncio.get_event_loop().call_later(call_info.delay,
                                                lambda: asyncio.get_event_loop()
                                                .create_task(self.start_sound_playback(peer, call_info.soundfile)))

    def _chan_notify_handler(self, msg):
        id = msg.params.get("targetid")
        if id not in self.active_calls:
            return
        if msg.params.get("reason", "") != "eof":
            return
        self._drop_call(id)

    def _drop_call(self, id):
        drop_msg = MessageRequest("call.drop", {"id": id})
        self.yate.send_message(drop_msg, fire_and_forget=True)
        del self.active_calls[id]

    def _chan_hangup_handler(self, msg):
        id = msg.params["id"]
        if id in self.active_calls:
            del self.active_calls[id]

    async def start_sound_playback(self, peer, soundfile):
        if peer not in self.active_calls:
            return # remote may have hung up
        attach_msg = MessageRequest("chan.masquerade", {
            "message": "chan.attach",
            "id": peer,
            "source": "wave/play/" + soundfile,
            "notify": peer,
        })
        await self.yate.send_message_async(attach_msg)

    def drop_call_if_not_answered(self, id):
        if id not in self.active_calls:
            return
        if not self.active_calls[id].answered:
            self._drop_call(id)

    def find_soundfile(self, name):
        for directory in self.sounds_directories:
            for ext in soundfile_extensions:
                test_path = Path(directory) / (name + ext)
                logging.debug("Testing %s for existence", test_path)
                if test_path.exists():
                    return str(test_path)

def main():
    parser = argparse.ArgumentParser(description='Yate CLI to generate automated calls.')
    parser.add_argument("port", type=int, help="The port at which yate is listening")
    parser.add_argument("sounds_directory", type=str, nargs="+", help="Directories at which we find the sounds")
    parser.add_argument("--bind_global", action="store_true")
    parser.add_argument("--trace", action="store_true", help="Enable debug tracing")


    args = parser.parse_args()
    if args.trace:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    app = YateCallGenerator(args.port, args.sounds_directory, args.bind_global)
    app.run()


if __name__ == "__main__":
    main()

