import asyncio
from asyncio.streams import StreamWriter, FlowControlMixin
import sys

from yate import yate
from yate.protocol import MessageRequest, Message, ConnectToYate

class YateAsync(yate.YateBase):
    MODE_STDIO = 1
    MODE_TCP = 2
    MODE_UNIX = 3

    def __init__(self, host=None, port=None, sockpath=None):
        super().__init__()
        self.event_loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(self.event_loop)
        self.reader = None
        self.writer = None
        self.main_task = None

        if host is not None:
            self.mode = self.MODE_TCP
            self.host = host
            self.port = port
        elif sockpath is not None:
            self.mode = self.MODE_UNIX
            self.sockpath = sockpath
        else:
            self.mode = self.MODE_STDIO

    def run(self, application_main):
        self.main_task = self.event_loop.create_task(self._amain(application_main))
        self.event_loop.run_until_complete(self.main_task)
        self.event_loop.close()

    async def _amain(self, application_main):
        if self.mode == self.MODE_STDIO:
            await self.setup_for_stdio()
        elif self.mode == self.MODE_TCP:
            await self.setup_for_tcp(self.host, self.port)
        elif self.mode == self.MODE_UNIX:
            await self.setup_for_unix(self.sockpath)
        else:
            raise NotImplementedError("Unknown mode of operation found")

        # now start event processing for yate messages
        message_loop_task = self.event_loop.create_task(self.message_processing_loop())
        # then let the main program run
        await self._amain_ready()
        try:
            await application_main(self)
        except asyncio.CancelledError as e:
            pass # We clean up even when the main task is cancelled
        self.writer.close()
        message_loop_task.cancel()

    async def _amain_ready(self):
        pass

    async def setup_for_stdio(self):
        self.reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(self.reader)
        await self.event_loop.connect_read_pipe(lambda: reader_protocol, sys.stdin)

        writer_transport, writer_protocol = await self.event_loop.connect_write_pipe(FlowControlMixin, sys.stdout)
        self.writer = StreamWriter(writer_transport, writer_protocol, None, self.event_loop)

    async def setup_for_tcp(self, host, port):
        self.reader, self.writer = await asyncio.open_connection(host, port, loop=self.event_loop)
        self.send_connect()

    async def setup_for_unix(self, sockpath):
        self.reader, self.writer = await asyncio.open_unix_connection(sockpath, loop=self.event_loop)
        self.send_connect()

    async def message_processing_loop(self):
        try:
            while True:
                raw_message = await self.reader.readline()
                if raw_message == b"":
                    break  # we only receive empty bytes if this is EOF, then terminate
                raw_message = raw_message.strip()
                self._recv_message_raw(raw_message)
            # once message processing ends, the whole application should terminate
        except asyncio.CancelledError:
            pass
        self.event_loop.stop()

    def _send_message_raw(self, msg):
        self.writer.write(msg + b"\n")

    async def drain(self):
        await self.writer.drain()

    async def register_message_handler_async(self, message, callback, priority=100, filter_attribute=None,
                                             filter_value=None):
        future = self.event_loop.create_future()

        def _done_callback(success):
            future.set_result(success)

        self.register_message_handler(message, callback, priority, filter_attribute, filter_value,
                                      done_callback=_done_callback)
        await future
        return future.result()

    async def register_watch_handler_async(self, message, callback):
        future = self.event_loop.create_future()

        def _done_callback(success):
            future.set_result(success)

        self.register_watch_handler(message, callback, _done_callback)
        await future
        return future.result()

    async def send_message_async(self, msg: MessageRequest) -> Message:
        future = self.event_loop.create_future()

        def _done_callback(old_msg, result_msg):
            future.set_result(result_msg)

        self.send_message(msg, _done_callback)
        await future
        return future.result()
