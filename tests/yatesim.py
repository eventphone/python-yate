import asyncio
from asyncio import Queue, CancelledError
from unittest.mock import MagicMock

from yate import protocol


class YateSimMessageHandler:
    def __init__(self, name, priority, filter_name, filter_value):
        self.name = name
        self.priority = priority
        self.filter_name = filter_name
        self.filter_value = filter_value

class YateSim:
    def __init__(self):
        self._mock_message_queue = None
        self._early_mock_message_queue = []
        self.installed_message_handlers = {}
        self._msg_id = 1
        self._session_id = "test"
        self.received_message_requests = []
        self._message_handlers = {}

    def set_message_handler(self, msg_name, handler):
        self._message_handlers[msg_name] = handler

    def set_out_message_queue(self, queue):
        self._mock_message_queue = queue

    def enqueue_yate_message_raw(self, yate_msg):
        # We need a running loop to setup the asyncio Queue object. So, buffer messages that are
        # injected in the test startup phase before the loop is running in a static queue. The YateSimAsyncMixin
        # will call flush_early_mock_message_queue once the real Queue is setup.
        if self._mock_message_queue:
            self._mock_message_queue.put_nowait(yate_msg)
        else:
            self._early_mock_message_queue.append(yate_msg)

    def flush_early_mock_message_queue(self):
        for msg in self._early_mock_message_queue:
            self._mock_message_queue.put_nowait(msg)
        self._early_mock_message_queue = []

    def enqueue_yate_message_request(self, msg_req: protocol.MessageRequest):
        msg_id = self._msg_id
        self._msg_id = self._msg_id + 1
        timestamp = self._msg_id * 10 # deterministic values for testing
        msg_id_str = "{}.{}".format(self._session_id, msg_id)

        raw_message = msg_req.encode(msg_id_str, timestamp)
        self.enqueue_yate_message_raw(raw_message)

    def generate_call_execute(self, channel:str, params: dict = {}):
        params["id"] = channel
        msg = protocol.MessageRequest("call.execute", params)
        self.enqueue_yate_message_request(msg)

    def send_dtmf(self, channel: str, symbol: str):
        msg = protocol.MessageRequest("chan.dtmf", {"id": channel, "text": symbol})
        self.enqueue_yate_message_request(msg)

    def process_message(self, msg: bytes):
        msg = protocol.parse_yate_message(msg)
        # we simulate minimal yate behavior and just ack all requests
        if isinstance(msg, protocol.InstallRequest):
            confirm = protocol.InstallConfirm(msg.priority, msg.name, True)
            handler = YateSimMessageHandler(msg.name, msg.priority, msg.filter_name, msg.filter_value)
            self.installed_message_handlers[msg.name] = handler
            self.enqueue_yate_message_raw(confirm.encode())
        elif isinstance(msg, protocol.UninstallRequest):
            success = msg.name in self.installed_message_handlers
            priority = self.installed_message_handlers[msg.name].priority if success else 0
            confirm = protocol.UninstallConfirm(priority, msg.name, success)
            self.enqueue_yate_message_raw(confirm.encode())
        elif isinstance(msg, protocol.WatchRequest):
            confirm = protocol.WatchConfirm(msg.name, True)
            self.enqueue_yate_message_raw(confirm.encode())
        elif isinstance(msg, protocol.UnwatchRequest):
            confirm = protocol.UnwatchConfirm(msg.name, True)
            self.enqueue_yate_message_raw(confirm.encode())
        elif isinstance(msg, protocol.Message):
            if not msg.reply:
                self.received_message_requests.append(msg)
                if msg.name in self._message_handlers:
                    self._message_handlers[msg.name](msg)
                self.enqueue_yate_message_raw(msg.encode_answer_for_yate(True))


class YateSimAsyncMixin:
    def __init__(self, yatesim: YateSim):
        super().__init__()
        self._mock_message_queue = None
        self._yate_sim = yatesim
        self.reader = MagicMock()
        self.writer = MagicMock()

    async def setup_for_stdio(self):
        # Setup mock message queue while running in event loop
        self._mock_message_queue = Queue()
        self._yate_sim.set_out_message_queue(self._mock_message_queue)
        self._yate_sim.flush_early_mock_message_queue()

    async def message_processing_loop(self):
        try:
            while True:
                raw_message = await self._mock_message_queue.get()
                if raw_message == b"":
                    # we only receive empty bytes if this is EOF, notify our program and terminate message
                    # processing loop
                    asyncio.create_task(self._yate_stream_closed())
                    break
                raw_message = raw_message.strip()
                self._recv_message_raw(raw_message)
            # once message processing ends, the whole application should terminate
        except CancelledError:
            pass

    # Hook normal message sending code and send it to the simulator instead
    def _send_message_raw(self, msg):
        self._yate_sim.process_message(msg)
