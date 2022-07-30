import asyncio
import unittest

from yate import ivr, protocol
from tests.yatesim import YateSim, YateSimAsyncMixin


class YateIVRInTheLoop(YateSimAsyncMixin, ivr.YateIVR):
    pass


class YateIVRBaseTests(unittest.TestCase):
    def setUp(self):
        self.ys = YateSim()
        self.ivr = YateIVRInTheLoop(self.ys)

    async def ivr_call_setup_test(self, ivr):
        self.assertEqual(ivr.call_id, "sip/4")

    def test_ivr_call_setup(self):
        self.ys.generate_call_execute("sip/4")
        self.ivr.run(self.ivr_call_setup_test)

    def check_message_handler(self, handler, prio, filter_name, filter_value):
        self.assertEqual(handler.priority, prio)
        self.assertEqual(handler.filter_name, filter_name)
        self.assertEqual(handler.filter_value, filter_value)

    async def ivr_message_handler_setup_test(self, ivr):
        self.assertSetEqual(set(self.ys.installed_message_handlers.keys()),
                            set(["chan.notify", "chan.dtmf"]))
        notify = self.ys.installed_message_handlers.get("chan.notify")
        self.check_message_handler(notify, 100, "targetid", "sip/1")

        dtmf = self.ys.installed_message_handlers.get("chan.dtmf")
        self.check_message_handler(dtmf, 100, "id", "sip/1")

    def test_ivr_message_handler_setup(self):
        self.ys.generate_call_execute("sip/1")
        self.ivr.run(self.ivr_message_handler_setup_test)

    async def simulate_hangup(self, ivr):
        # When the call is hung up, yate will close our stdin.
        def hangupHandler():
            self.hangup = True
        ivr.register_hangup_handler(hangupHandler)
        # simulate channel termination by adding an empty message
        self.ys.enqueue_yate_message_raw(b"")
        await asyncio.sleep(10)

    def test_hangup_handler(self):
        self.hangup = False
        self.ys.generate_call_execute("sip/1")
        self.assertFalse(self.hangup)
        self.ivr.run(self.simulate_hangup)
        self.assertTrue(self.hangup)

    def test_play_soundfile(self):
        async def play_sndfile_main(ivr):
            await ivr.play_soundfile("/var/opt/test.slin", repeat=True)

        self.ys.generate_call_execute("sip/1")
        self.ivr.run(play_sndfile_main)
        attach_msg = self.ys.received_message_requests[0]
        self.assertEqual("chan.attach", attach_msg.name)
        self.assertDictEqual(attach_msg.params,
                             {"source": "wave/play//var/opt/test.slin",
                              "notify": "sip/1",
                              "autorepeat": "true"})

    async def play_sndfile_wait_main(self, ivr):
        notify_msg = protocol.MessageRequest("chan.notify", {"id": "sip/1", "reason": "eof"})
        self.ys.enqueue_yate_message_request(notify_msg)
        await ivr.play_soundfile("/var/opt/test.slin", complete=True)
        self.sound_finished = True

    def test_play_soundfile_wait(self):
        self.sound_finished = False
        self.ys.generate_call_execute("sip/1")

        self.ivr.run(self.play_sndfile_wait_main)
        self.assertTrue(self.sound_finished)

    async def dtmf_read_until_test_main(self, ivr):
        self.ys.send_dtmf("sip/1", "4")
        self.ys.send_dtmf("sip/1", "7")
        self.ys.send_dtmf("sip/1", "1")
        self.ys.send_dtmf("sip/1", "1")
        self.ys.send_dtmf("sip/1", "#")

        dtmf_input = await ivr.read_dtmf_until("#")
        self.assertEqual("4711#", dtmf_input)
        self.finished = True

    def test_dtmf_read_until(self):
        self.finished = False
        self.ys.generate_call_execute("sip/1")

        self.ivr.run(self.dtmf_read_until_test_main)
        self.assertTrue(self.finished)

    async def dtmf_read_symbols_test_main(self, ivr):
        self.ys.send_dtmf("sip/1", "4")
        self.ys.send_dtmf("sip/1", "7")
        self.ys.send_dtmf("sip/1", "1")
        self.ys.send_dtmf("sip/1", "2")
        self.ys.send_dtmf("sip/1", "*")

        dtmf_input = await ivr.read_dtmf_symbols(3)
        self.assertEqual("471", dtmf_input)
        self.finished = True

    def test_dtmf_read_symbols(self):
        self.finished = False
        self.ys.generate_call_execute("sip/1")

        self.ivr.run(self.dtmf_read_symbols_test_main)
        self.assertTrue(self.finished)
        self.assertEqual("2*", self.ivr.dtmf_buffer)

    async def wait_channel_event_test_main(self, i):
        self.ys.send_dtmf("sip/1", "4")

        event = await i.wait_channel_event()
        self.assertEqual(event, ivr.ChannelEventType.DTMF)
        self.finished = True

    def test_dtmf_read_symbols(self):
        self.finished = False
        self.ys.generate_call_execute("sip/1")

        self.ivr.run(self.wait_channel_event_test_main)
        self.assertTrue(self.finished)

    async def dtmf_timeout_test_main(self, ivr):
        self.ys.send_dtmf("sip/1", "1")
        result = await ivr.read_dtmf_until("#", timeout_s=0.01)
        self.assertEqual("1", result)
        self.finished = True

    def test_dtmf_timeout(self):
        self.finished = False
        self.ys.generate_call_execute("sip/1")

        self.ivr.run(self.dtmf_timeout_test_main)
        self.assertTrue(self.finished)
