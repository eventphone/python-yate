import unittest
from unittest.mock import patch

from yate.yate import YateBase


class YateBaseMessageHandlerSetupTests(unittest.TestCase):

    @patch.object(YateBase, "_send_message_raw")
    def test_message_handler_install(self, mock_method):
        yate = YateBase()
        yate.register_message_handler("call.execute", lambda: True, 100, "myattrib", "myvalue")

        self.assertIn("call.execute", yate._message_handlers)

        handler = yate._message_handlers["call.execute"]
        self.assertEqual("call.execute", handler.message)
        self.assertEqual("100", str(handler.priority))
        self.assertEqual("myattrib", handler.filter_attribute)
        self.assertEqual("myvalue", handler.filter_value)
        self.assertFalse(handler.installed)
        self.assertFalse(handler.uninstalled)

        mock_method.assert_called_with(b"%%>install:100:call.execute:myattrib:myvalue")

        # now simulate that yate responded correctly
        yate._recv_message_raw(b"%%<install:100:call.execute:true")
        self.assertTrue(handler.installed)




if __name__ == '__main__':
    unittest.main()
