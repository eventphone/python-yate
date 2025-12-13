import asyncio
from asyncio.streams import StreamWriter, FlowControlMixin
import sys
import logging

from yate import yate
from yate.protocol import MessageRequest, Message, ConnectToYate

logger = logging.getLogger("yate")


class YateAsync(yate.YateBase):
    MODE_STDIO = 1
    MODE_TCP = 2
    MODE_UNIX = 3

    def __init__(self, host=None, port=None, sockpath=None):
        super().__init__()
        self.reader = None
        self.writer = None
        self.main_task = None
        self._automatic_bufsize = False
        self._termination_handler = None

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
        asyncio.run(self._amain(application_main))

    def set_termination_handler(self, termination_handler):
        self._termination_handler = termination_handler

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
        message_loop_task = asyncio.create_task(self.message_processing_loop())
        # then let the main program run
        await self._amain_ready()
        try:
            self.main_task = asyncio.create_task(application_main(self))
            await self.main_task
        except asyncio.CancelledError as e:
            pass # We clean up even when the main task is cancelled
        self.writer.close()
        message_loop_task.cancel()

    async def _amain_ready(self):
        pass

    async def setup_for_stdio(self):
        self.reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(self.reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: reader_protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(FlowControlMixin, sys.stdout)
        self.writer = StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())

    async def setup_for_tcp(self, host, port):
        self.reader, self.writer = await asyncio.open_connection(host, port)
        self.send_connect()

    async def setup_for_unix(self, sockpath):
        self.reader, self.writer = await asyncio.open_unix_connection(sockpath)
        self.send_connect()

    async def message_processing_loop(self):
        try:
            while True:
                raw_message = await self.reader.readline()
                logger.debug("< %s", repr(raw_message.strip()))
                if raw_message == b"":
                    # we only receive empty bytes if this is EOF, notify our program and terminate message
                    # processing loop
                    asyncio.create_task(self._yate_stream_closed())
                    break
                raw_message = raw_message.strip()
                self._recv_message_raw(raw_message)
            # once message processing ends, the whole application should terminate
        except asyncio.CancelledError:
            pass

    def _send_message_raw(self, msg):
        if self._automatic_bufsize:
            yate_buf_required = len(msg) + 2 # plus \n and \0 terminator in yate
            if yate_buf_required > int(self.get_local("bufsize")):
                def deferred_msg_write(_param, _value, _success):
                    # defer writing the message that is too long until the bufsize was adapted
                    self.writer.write(msg + b"\n")
                    logger.debug("> %s", repr(msg))
                # round to next kb
                requested_bufsize = ((yate_buf_required // 1024) + 1) * 1024
                logger.info("Automatic buffer size increase to %d bytes",  requested_bufsize)
                self.set_local("bufsize", str(requested_bufsize), done_callback=deferred_msg_write)
                return
        self.writer.write(msg + b"\n")
        logger.debug("> %s", repr(msg))

    async def _yate_stream_closed(self):
        if self._termination_handler is not None:
            self._termination_handler()

    async def drain(self):
        await self.writer.drain()

    async def register_message_handler_async(self, message, callback, priority=100, filter_attribute=None,
                                             filter_value=None):
        future = asyncio.get_event_loop().create_future()

        def _done_callback(success):
            future.set_result(success)

        self.register_message_handler(message, callback, priority, filter_attribute, filter_value,
                                      done_callback=_done_callback)
        await future
        return future.result()

    async def register_watch_handler_async(self, message, callback):
        future = asyncio.get_event_loop().create_future()

        def _done_callback(success):
            future.set_result(success)

        self.register_watch_handler(message, callback, _done_callback)
        await future
        return future.result()

    async def send_message_async(self, msg: MessageRequest) -> Message:
        future = asyncio.get_event_loop().create_future()

        def _done_callback(old_msg, result_msg):
            future.set_result(result_msg)

        self.send_message(msg, _done_callback)
        await future
        return future.result()

    async def set_local_async(self, param, value):
        future = asyncio.get_event_loop().create_future()

        def done_callback(_param, _value, success):
            future.set_result(success)

        self.set_local(param, value, done_callback=done_callback)
        await future
        return future.result()

    async def get_local_async(self, param):
        if param in self._local_params:
            return self._local_params[param]

        future = asyncio.get_event_loop().create_future()

        def done_callback(_param, value, _success):
            future.set_result(value)

        self.set_local(param, "", done_callback=done_callback)
        await future
        return future.result()

    async def activate_automatic_bufsize(self):
        await self.get_local_async("bufsize")
        self._automatic_bufsize = True