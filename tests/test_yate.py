import unittest
from unittest.mock import patch, MagicMock

from yate import yate
from yate.protocol import Message, MessageRequest
from yate.yate import YateBase


class YateBaseMessageHandlerSetupTests(unittest.TestCase):
    @patch.object(YateBase, "_send_message_raw")
    def test_message_handler_install(self, mock_method):
        y = YateBase()
        y.register_message_handler("call.execute", lambda: True, 100, "myattrib", "myvalue")

        self.assertIn("call.execute", y._message_handlers)

        handler = y._message_handlers["call.execute"]
        self.assertEqual("call.execute", handler.message)
        self.assertEqual("100", str(handler.priority))
        self.assertEqual("myattrib", handler.filter_attribute)
        self.assertEqual("myvalue", handler.filter_value)
        self.assertFalse(handler.installed)
        self.assertFalse(handler.uninstalled)

        mock_method.assert_called_with(b"%%>install:100:call.execute:myattrib:myvalue")

        # now simulate that yate responded correctly
        y._recv_message_raw(b"%%<install:100:call.execute:true")
        self.assertTrue(handler.installed)

    def test_message_handler_install_done_callback(self):
        y = YateBase()
        done_callback_mock = MagicMock()
        y.register_message_handler("call.execute", lambda: True, 100, "myattrib", "myvalue",
                                   done_callback=done_callback_mock)
        done_callback_mock.assert_not_called()

        y._recv_message_raw(b"%%<install:100:call.execute:true")
        done_callback_mock.assert_called_with(True)

    @patch.object(YateBase, "_send_message_raw")
    def test_message_handler_noinstall(self, mock_method):
        y = YateBase()
        y.register_message_handler("call.execute", lambda: True, install=False)

        self.assertIn("call.execute", y._message_handlers)

        handler = y._message_handlers["call.execute"]
        self.assertEqual("call.execute", handler.message)

        mock_method.assert_not_called()

    @patch.object(YateBase, "_send_message_raw")
    def test_message_handler_uninstall(self, mock_method):
        y = YateBase()
        mh = yate.MessageHandler("call.execute", 80, lambda: True, None, None)
        mh.installed = True
        y._message_handlers["call.execute"] = mh

        y.unregister_message_handler("call.execute")
        self.assertEqual(True, mh.uninstalled)
        mock_method.assert_called_with(b"%%>uninstall:call.execute")

        y._recv_message_raw(b"%%<uninstall:80:call.execute:true")
        self.assertNotIn("call.execute", y._message_handlers)

    def test_installed_message_handler_dispatch(self):
        y = YateBase()
        callback_mock = MagicMock()
        mh = yate.MessageHandler("call.execute", 80, callback_mock, None, None)
        mh.installed = True
        y._message_handlers["call.execute"] = mh

        msg = Message("0xdeadc0de", 4711, "call.execute", "false", {"caller": "me", "target": "0815"})
        self.assertEqual("message", msg.msg_type)
        self.assertFalse(msg.reply)

        y._handle_yate_message(msg)
        callback_mock.assert_called_with(msg)

        callback_mock.reset_mock()
        msg2 = Message("0xdeadbeef", 4712, "chan.attach", "false", {})
        y._handle_yate_message(msg2)
        callback_mock.assert_not_called()


class YateMessageProcessingTests(unittest.TestCase):
    def setUp(self):
        self.y = YateBase()
        self.y._get_timestamp = MagicMock()

    @patch.object(YateBase, "_send_message_raw")
    def test_message_encoding(self, moc_method):
        msg = MessageRequest("chan.attach", {"target": "sip/5"}, "res")

        self.y._get_timestamp.return_value = 1234
        self.y.send_message(msg, fire_and_forget=True)
        moc_method.assert_called_with(b"%%>message:" + self.y._session_id.encode()
                                      + b".1:1234:chan.attach:res:target=sip/5")

        moc_method.reset_mock()

        self.y._get_timestamp.return_value = 1546
        self.y.send_message(msg, fire_and_forget=True)
        moc_method.assert_called_with(b"%%>message:" + self.y._session_id.encode()
                                      + b".2:1546:chan.attach:res:target=sip/5")

    def test_message_response_callback_mechanism(self):
        callback_mock = MagicMock()
        self.y._get_timestamp.return_value = 42

        msg = MessageRequest("chan.attach", {"target": "sip/2"}, "resultVal")
        self.y.send_message(msg, callback_mock)
        self.assertIn(self.y._session_id + ".1", self.y._requested_messages)

        msg_reply = Message(self.y._session_id + ".1", 42, "chan.attach", "result",
                            {"target": "sip/2", "notify": "true"}, reply=True)
        self.y._handle_yate_message(msg_reply)

        self.assertNotIn(self.y._session_id + ".1", self.y._requested_messages)
        callback_mock.assert_called_with(msg, msg_reply)

    @patch.object(YateBase, "_send_message_raw")
    def test_message_answer_mechanism(self, mock_method):
        callback_mock = MagicMock()
        mh = yate.MessageHandler("call.execute", 80, callback_mock, None, None)
        mh.installed = True
        self.y._message_handlers["call.execute"] = mh

        msg = Message("0xdeadc0de", 4711, "call.execute", "false", {"caller": "me", "target": "0815"})
        self.y._handle_yate_message(msg)
        callback_mock.assert_called_with(msg)

        msg.params["caller"] = "you"
        self.y.answer_message(msg, True)
        self.assertGreaterEqual(len(mock_method.mock_calls), 1)
        answer_raw = mock_method.call_args[0][0]
        self.assertTrue(answer_raw.startswith(b"%%<message:0xdeadc0de:true:call.execute:false:"))
        self.assertTrue(answer_raw.find(b"caller=you") >= 0)
        self.assertTrue(answer_raw.find(b"target=0815") >= 0)

    @patch.object(YateBase, "_send_message_raw")
    def test_message_answer_from_return_value(self, mock_method):
        callback_mock = MagicMock()
        callback_mock.return_value = True

        mh = yate.MessageHandler("call.execute", 80, callback_mock, None, None)
        mh.installed = True
        self.y._message_handlers["call.execute"] = mh

        msg = Message("0xdeadc0de", 4711, "call.execute", "false", {"caller": "me", "target": "0815"})
        self.y._handle_yate_message(msg)
        callback_mock.assert_called_with(msg)

        self.assertGreaterEqual(len(mock_method.mock_calls), 1)
        answer_raw = mock_method.call_args[0][0]
        self.assertTrue(answer_raw.startswith(b"%%<message:0xdeadc0de:true:call.execute:false:"))
        self.assertTrue(answer_raw.find(b"caller=me") >= 0)
        self.assertTrue(answer_raw.find(b"target=0815") >= 0)

    @patch.object(YateBase, "_send_message_raw")
    def test_answers_uninteresting_messages(self, mock_method):
        self.y._recv_message_raw(b"%%>message:0xbeef:1415:call.hangup:ret:channel=dump/3")
        mock_method.assert_called_with(b"%%<message:0xbeef:false:call.hangup:ret:channel=dump/3")



class YateWatchProcessingTests(unittest.TestCase):
    def setUp(self):
        self.y = YateBase()

    @patch.object(YateBase, "_send_message_raw")
    def test_install_watch_handler(self, mock_method):
        self.y.register_watch_handler("chan.notify", lambda: True)

        self.assertIn("chan.notify", self.y._watch_handlers)
        handler = self.y._watch_handlers["chan.notify"]
        self.assertFalse(handler.installed)
        self.assertFalse(handler.uninstalled)
        mock_method.assert_called_with(b"%%>watch:chan.notify")

        self.y._recv_message_raw(b"%%<watch:chan.notify:true")
        self.assertTrue(handler.installed)

    def test_install_watch_handler_done_callback(self):
        done_callback_mock = MagicMock()
        self.y.register_watch_handler("chan.notify", lambda: True, done_callback=done_callback_mock)
        done_callback_mock.assert_not_called()

        self.y._recv_message_raw(b"%%<watch:chan.notify:true")
        done_callback_mock.assert_called_with(True)

    @patch.object(YateBase, "_send_message_raw")
    def test_uninstall_watch_handler(self, mock_method):
        handler = yate.WatchHandler("chan.notify", lambda: True)
        handler.installed = True
        self.y._watch_handlers["chan.notify"] = handler

        self.y.unregister_watch_handler("chan.notify")
        mock_method.assert_called_with(b"%%>unwatch:chan.notify")
        self.assertTrue(handler.uninstalled)

        self.y._recv_message_raw(b"%%<unwatch:chan.notify:true")
        self.assertNotIn("chan.notify", self.y._watch_handlers)

    def test_watch_handler_recv_message(self):
        callback_mock = MagicMock()
        handler = yate.WatchHandler("chan.notify", callback_mock)
        handler.installed = True
        self.y._watch_handlers["chan.notify"] = handler

        msg = Message("0xDEAD.1", None, "chan.notify", "val", {"target": "wave/2"}, True, True)
        self.y._handle_yate_message(msg)

        callback_mock.assert_called_with(msg)

    def test_universal_watch_handler_recv_message(self):
        callback_mock = MagicMock()
        handler = yate.WatchHandler("", callback_mock)
        handler.installed = True
        self.y._watch_handlers[""] = handler

        msg = Message("0xDEAD.1", None, "chan.dtmf", "val", {"target": "wave/2"}, True, True)
        self.y._handle_yate_message(msg)

        callback_mock.assert_called_with(msg)


class YateConnectTests(unittest.TestCase):
    @patch.object(YateBase, "_send_message_raw")
    def test_connect(self, mock_method):
        y = YateBase()
        y.send_connect()
        mock_method.assert_called_with(b"%%>connect:global")


class YateSetLocalTests(unittest.TestCase):
    def setUp(self):
        self.y = YateBase()

    @patch.object(YateBase, "_send_message_raw")
    def test_setlocal(self, mock_method):
        done_callback_mock = MagicMock()
        self.y.set_local("id", "mychan0", done_callback=done_callback_mock)
        done_callback_mock.assert_not_called()
        self.assertIn("id", self.y._local_param_handlers)
        mock_method.assert_called_with(b"%%>setlocal:id:mychan0")

        self.y._recv_message_raw(b"%%<setlocal:id:mychan0:true")
        done_callback_mock.assert_called_with("id", "mychan0", True)
        self.assertEqual(self.y.get_local("id"), "mychan0")
        self.assertNotIn("id", self.y._local_param_handlers)


if __name__ == '__main__':
    unittest.main()
