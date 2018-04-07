import unittest
from unittest.mock import patch, MagicMock

from yate import yate
from yate.protocol import MessageFromYate
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

        msg = MessageFromYate("0xdeadc0de", 4711, "call.execute", "false", {"caller": "me", "target": "0815"})
        self.assertEqual("message", msg.msg_type)
        self.assertFalse(msg.reply)

        y._handle_yate_message(msg)
        callback_mock.assert_called_with(msg)

        callback_mock.reset_mock()
        msg2 = MessageFromYate("0xdeadbeef", 4712, "chan.attach", "false", {})
        y._handle_yate_message(msg2)
        callback_mock.assert_not_called()

if __name__ == '__main__':
    unittest.main()
