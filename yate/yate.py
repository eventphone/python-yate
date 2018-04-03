import logging

from yate.protocol import parse_yatemessage, InstallToYate, InstallFromYate, MessageFromYate

logger = logging.getLogger("yate")

class MessageHandler:
    def __init__(self, msg, prio, callback, filter_attribute, filter_name):
        self.message = msg
        self.priority = prio
        self.callback = callback
        self.filter_attribute = filter_attribute
        self.filter_name = filter_name
        self.installed = False


class WatchHandler:
    def __init__(self, msg, callback):
        self.callback = callback
        self.installed = False


class Yate:
    def __init__(self):
        self._message_handlers = {}
        self._watch_handlers = {}

    def register_message_handler(self, message, callback, priority=100, filter_attribute=None, filter_value=None):
        handler = MessageHandler(message, priority, callback, filter_attribute, filter_value)
        self._message_handlers[message] = handler
        install_msg = InstallToYate(priority.message, filter_attribute, filter_value)
        self._send_message_raw(install_msg.encode())

    def unregister_message_handler(self, message):
        pass

    def register_watch_handler(self, message, callback):
        pass

    def _internal_messsage_handler(self, raw_data):
        try:
            message = parse_yatemessage(raw_data)
            message.yate = self
        except Exception as e:
            logging.error("Incoming yate message did not parse: {}".format(str(e)))
            return # for now ignore messages with parsing errors
        if isinstance(message, InstallFromYate):
            handler = self._message_handlers.get(message.name)
            if handler is None:
                logger.warning("Yate notified us that a handler for {} is installed though we didn't request it".format(message.name))
            handler.installed = True
        elif isinstance(message, MessageFromYate):
            handler = self._message_handlers.get(message.name)
            if handler is None:
                logger.warning("Yate sent us a message we did not subscribe for: {}".format(message.name))
                return
            handler.callback(message)

    def _send_message_raw(self, msg):
        pass