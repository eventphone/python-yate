import logging
import random
import string
import time

from yate.protocol import parse_yate_message, InstallRequest, UninstallRequest, WatchRequest, UnwatchRequest, ConnectToYate, SetLocalRequest

logger = logging.getLogger("yate")


class MessageHandler:
    def __init__(self, msg, prio, callback, filter_attribute, filter_value, done_callback=None):
        self.message = msg
        self.priority = prio
        self.callback = callback
        self.filter_attribute = filter_attribute
        self.filter_value = filter_value
        self.installed = False
        self.uninstalled = False
        self.done_callback = done_callback


class MessageRequest:
    def __init__(self, message_object, id, timestamp, callback):
        self.msg = message_object
        self.id = id
        self.timestamp = timestamp
        self.callback = callback


class WatchHandler:
    def __init__(self, msg, callback, done_callback=None):
        self.message = msg
        self.callback = callback
        self.installed = False
        self.uninstalled = False
        self.done_callback = done_callback


def session_id_generator():
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


class YateBase:
    def __init__(self):
        self._message_handlers = {}
        self._watch_handlers = {}
        self._requested_messages = {}
        self._local_params = {}
        self._local_param_handlers = {}
        self._msg_id = 1
        self._session_id = session_id_generator()

    def send_connect(self):
        msg = ConnectToYate()
        self._send_message_raw(msg.encode())

    def register_message_handler(self, message, callback, priority=100, filter_attribute=None, filter_value=None,
                                 install=True, done_callback=None):
        handler = MessageHandler(message, priority, callback, filter_attribute, filter_value, done_callback)
        self._message_handlers[message] = handler
        if install:
            install_msg = InstallRequest(priority, message, filter_attribute, filter_value)
            self._send_message_raw(install_msg.encode())

    def unregister_message_handler(self, message):
        if message not in self._message_handlers:
            return
        handler = self._message_handlers[message]
        if handler.installed:
            uninstall_msg = UninstallRequest(message)
            self._send_message_raw(uninstall_msg.encode())
            handler.uninstalled = True
        else:
            # if it was never installed - well just remove it from the registry
            del self._message_handlers[message]

    def register_watch_handler(self, message, callback, done_callback=None):
        handler = WatchHandler(message, callback, done_callback)
        self._watch_handlers[message] = handler
        watch_msg = WatchRequest(message)
        self._send_message_raw(watch_msg.encode())

    def unregister_watch_handler(self, message):
        if message not in self._watch_handlers:
            return
        handler = self._watch_handlers[message]
        if handler.installed:
            unwatch_msg = UnwatchRequest(message)
            self._send_message_raw(unwatch_msg.encode())
            handler.uninstalled = True
        else:
            del self._watch_handlers[message]

    def set_local(self, param, value, done_callback=None):
        if done_callback is not None:
            self._local_param_handlers[param] = done_callback
        setlocal_msg = SetLocalRequest(param, value)
        self._send_message_raw(setlocal_msg.encode())

    def get_local(self, param):
        return self._local_params.get(param)

    def send_message(self, msg, callback=None, fire_and_forget=False):
        msg_id = self._msg_id
        self._msg_id = self._msg_id + 1
        timestamp = self._get_timestamp()
        msg_id_str = "{}.{}".format(self._session_id, msg_id)

        raw_message = msg.encode(msg_id_str, timestamp)
        self._send_message_raw(raw_message)

        if not fire_and_forget:
            req = MessageRequest(msg, msg_id_str, timestamp, callback)
            self._requested_messages[msg_id_str] = req

    def answer_message(self, msg, processed):
        raw_message = msg.encode_answer_for_yate(processed)
        self._send_message_raw(raw_message)

    def _handle_yate_install(self, msg):
        handler = self._message_handlers.get(msg.name)
        if handler is None:
            logger.warning("Yate notified us that a handler for {} is installed though we didn't request it".format(msg.name))
            return
        if msg.success:
            handler.installed = True
        if handler.done_callback is not None:
            handler.done_callback(msg.success)

    def _handle_yate_uninstall(self, msg):
        handler = self._message_handlers.get(msg.name)
        if handler is None:
            logger.warning("Yate notified us that a handler for {} is uninstalled though we didn't request it".format(msg.name))
            return
        del self._message_handlers[msg.name]

    def _handle_yate_watch(self, msg):
        handler = self._watch_handlers.get(msg.name)
        if handler is None:
            logger.warning("Yate notified us that{} is watched though we didn't request it".format(msg.name))
            return
        if msg.success:
            handler.installed = True
        if handler.done_callback is not None:
            handler.done_callback(msg.success)

    def _handle_yate_unwatch(self, msg):
        handler = self._watch_handlers.get(msg.name)
        if handler is None:
            logger.warning("Yate notified us that {} is not watched anymore though we didn't request it".format(msg.name))
            return
        del self._watch_handlers[msg.name]

    def _handle_yate_setlocal(self, msg):
        self._local_params[msg.param] = msg.value
        if msg.param in self._local_param_handlers:
            self._local_param_handlers[msg.param](msg.param, msg.value, msg.success)
            del self._local_param_handlers[msg.param]

    def _handle_yate_message(self, msg):
        if msg.reply is False:
            handler = self._message_handlers.get(msg.name)
            if handler is None:
                logger.warning("Yate sent us a message we did not subscribe for: {}".format(msg.name))
                # in order to keep normal event processing, just ack and explain we did not process it
                self.answer_message(msg, False)
                return
            result = handler.callback(msg)
            # handlers can return true or false if they want us to automatically answer the message
            if result is not None:
                self.answer_message(msg, result)
        else:
            req = self._requested_messages.get(msg.id)
            if req is None:
                # this might be a watched message type
                handler = self._watch_handlers.get(msg.name)
                if handler is None:
                    # maybe there is a watch handler for everything
                    handler = self._watch_handlers.get("")
                    if handler is None:
                        # this is probably caused by fire and forget mode
                        logger.debug("Got unprocessed message of type {}".format(msg.name))
                        return
                handler.callback(msg)
            else:
                req.callback(req.msg, msg)
                del self._requested_messages[msg.id]

    def _get_timestamp(self):
        # This function exists mostly for test mocking
        return int(time.time())

    def _send_message_raw(self, msg):
        pass

    def _recv_message_raw(self, raw_data):
        try:
            message = parse_yate_message(raw_data)
        except Exception as e:
            logging.error("Incoming yate message did not parse: {}".format(str(e)))
            return  # for now ignore messages with parsing errors
        if hasattr(self, "_handle_yate_{}".format(message.msg_type)):
            getattr(self, "_handle_yate_{}".format(message.msg_type))(message)
