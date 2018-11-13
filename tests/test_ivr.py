import unittest

from yate import ivr
from tests.yatesim import YateSim, YateSimAsyncMixin


class YateIVRInTheLoop(YateSimAsyncMixin, ivr.YateIVR):
    pass


class YateIVRBaseTests(unittest.TestCase):
    def setUp(self):
        self.ys = YateSim()
        self.ivr = YateIVRInTheLoop(self.ys)

    async def ivr_call_setup_test(self, ivr):
        self.assertEqual(ivr.chan_id, "sip/4")

    def test_ivr_call_setup(self):
        self.ys.generate_call_execute("sip/4")
        self.ivr.run(self.ivr_call_setup_test)

    def check_message_handler(self, handler, prio, filter_name, filter_value):
        self.assertEqual(handler.priority, prio)
        self.assertEqual(handler.filter_name, filter_name)
        self.assertEqual(handler.filter_value, filter_value)

    async def ivr_message_handler_setup_test(self, ivr):
        self.assertSetEqual(set(self.ys.installed_message_handlers.keys()),
                            set(["chan.notify", "chan.dtmf", "chan.hangup"]))
        notify = self.ys.installed_message_handlers.get("chan.notify")
        self.check_message_handler(notify, 100, "targetid", "sip/1")

        dtmf = self.ys.installed_message_handlers.get("chan.dtmf")
        self.check_message_handler(dtmf, 100, "id", "sip/1")

        hangup = self.ys.installed_message_handlers.get("chan.hangup")
        self.check_message_handler(hangup, 100, "id", "sip/1")

    def test_ivr_message_handler_setup(self):
        self.ys.generate_call_execute("sip/1")
        self.ivr.run(self.ivr_message_handler_setup_test)
