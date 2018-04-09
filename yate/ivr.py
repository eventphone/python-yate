import asyncio

from yate.asyncio import YateAsync


class YateIVR(YateAsync):
    def __init__(self):
        super().__init__()
        self._call_ready_future = self.event_loop.create_future()
        self._notify_future = None
        self.call_params = {}
        self.dtmf_buffer = []
        # register a listener that takes the call.execute message from yate for the incoming call
        self.register_message_handler("call.execute", self._initial_call_execute_handler, install=False)

    def _initial_call_execute_handler(self, msg):
        self.call_params = msg.params
        self.chan_id = msg.params["id"]
        self.event_loop.create_task(self._install_ivr_handlers())
        self.unregister_message_handler("call.execute")
        return True  # Acknowledge that we accepted the call

    def _chan_notify_handler(self, msg):
        if self._notify_future is not None and self._notify_future.done() is False:
            self._notify_future.set_result(msg.params.get("reason", ""))

    def _chan_dtmf_handler(self, msg):
        self.dtmf_buffer.append(msg.params["text"])
        return True

    def _chan_hangup_handler(self, msg):
        self.main_task.cancel()
        return True

    async def _install_ivr_handlers(self):
        await self.register_message_handler_async("chan.notify", self._chan_notify_handler, 100, "targetid",
                                                  self.chan_id)
        await self.register_message_handler_async("chan.dtmf", self._chan_dtmf_handler, 100, "id", self.chan_id)
        await self.register_message_handler_async("chan.hangup", self._chan_dtmf_handler, 100, "id", self.chan_id)
        self._call_ready_future.set_result(None)

    async def _amain_ready(self):
        # wait for yate to pass us our call.execute event and install all default handlers
        await self._call_ready_future
        # well, now we can proceed to applications main

