def yate_decode_bytes(byte_input):
    output = b""
    escaped = False
    for b in byte_input:
        if escaped:
            if b == ord("%"):
                output += bytes([b])
            else:
                if b < 64:
                    raise YateMessageParsingError("Received invalid yate encoding: {} after %".format(hex(b)))
                output += bytes([(b-64)])
            escaped = False
        else:
            if b == ord("%"):
                escaped = True
            else:
                output += bytes([b])
    return output


def yate_encode_bytes(byte_input):
    output = b""
    for b in byte_input:
        if b < 32 or b == ord(":"):
            output += b"%"+bytes([(b+64)])
        elif b == ord("%"):
            output += b"%%"
        else:
            output += bytes([b])
    return output


def yate_decode_split(bytes_input):
    output = bytes_input.split(b":")
    output = [yate_decode_bytes(param).decode("utf-8") for param in output]
    return output


def yate_encode_join(*args):
    output = [yate_encode_bytes(param.encode("utf-8")) for param in args]
    return b":".join(output)


def yate_parse_keyvalue(params):
    output = {}
    for param in params:
        res = param.split("=", 1)
        if len(res) == 2:
            key, value = res
        else:
            key = param
            value = ""
        output[key] = value
    return output


class YateMessageParsingError(Exception):
    def __init__(self, message):
        super().__init__(message)


def parse_yate_message(bytes_input):
    split_msg = yate_decode_split(bytes_input)
    message_type = split_msg[0]
    message_class = _yate_message_type_table.get(message_type)
    if message_class is None:
        raise YateMessageParsingError("Unknown message type: {}".format(message_type))
    return message_class.parse(split_msg)


class Message:
    @classmethod
    def parse(cls, data):
        if len(data) < 5:
            raise YateMessageParsingError("Invalid message from yate with only {} parameters".format(len(data)))
        reply = (data[0] == "%<message")
        id = data[1]
        if reply:
            time = None
            processed = data[2].lower() == "true"
        else:
            processed = None
            try:
                time = int(data[2])
            except ValueError:
                raise YateMessageParsingError("Invalid message time from yate: {}".format(data[2]))
        name = data[3]
        return_value = data[4]
        params = yate_parse_keyvalue(data[5:])
        return cls(id, time, name, return_value, params, processed, reply)

    def __init__(self, id, time, name, return_value, params, processed=None, reply=False):
        self.msg_type = "message"
        self.id = id
        self.time = time
        self.processed = processed
        self.name = name
        self.return_value = return_value
        self.params = params
        self.reply = reply

    def encode_answer_for_yate(self, processed):
        processed = str(processed).lower()
        return yate_encode_join("%<message",
                                self.id,
                                processed,
                                self.name,
                                self.return_value,
                                *["=".join(item) for item in self.params.items()])


class MessageRequest:
    def __init__(self, name, params, return_value=""):
        self.name = name
        self.return_value = return_value
        self.params = params

    def encode(self, id, timestamp):
        return yate_encode_join("%>message",
                                id,
                                str(int(timestamp)),
                                self.name,
                                self.return_value,
                                *["=".join(item) for item in self.params.items()])


class InstallRequest:
    def __init__(self, prioriy, name, filtername=None, filtervalue=None):
        self.priority = prioriy
        self.name = name
        self.filter_name = filtername
        self.filter_value = str(filtervalue)

    @classmethod
    def parse(cls, data):
        if len(data) < 3:
            raise YateMessageParsingError("Invalid install request with only {} parameters".format(len(data)))
        priority = int(data[1])
        name = data[2]
        filter_name = data[3] if len(data) >= 4 else None
        filter_value = data[4] if len(data) >= 5 else None
        return cls(priority, name, filter_name, filter_value)

    def encode(self):
        extraargs = []
        if self.filter_name is not None:
            extraargs.append(self.filter_name)
            if self.filter_value is not None:
                extraargs.append(self.filter_value)
        return yate_encode_join("%>install", str(self.priority), self.name, *extraargs)


class InstallUninstallBase:
    @classmethod
    def parse(cls, data):
        if len(data) < 4:
            raise YateMessageParsingError("Invalid install/uninstall from yate with only {} parameters".format(len(data)))
        try:
            priority = int(data[1])
        except ValueError:
            raise YateMessageParsingError("Invalid priority value received: {}".format(data[1]))
        name = data[2]
        success = data[3].lower() == "true"
        return cls(priority, name, success)


class InstallConfirm(InstallUninstallBase):
    def __init__(self, priority, name, success):
        self.msg_type = "install"
        self.priority = priority
        self.name = name
        self.success = success

    def encode(self):
        return yate_encode_join("%<install", str(self.priority), self.name, str(self.success).lower())


class UninstallRequest:
    def __init__(self, name):
        self.name = name

    @classmethod
    def parse(cls, data):
        if len(data) != 2:
            raise YateMessageParsingError("Invalid uninstall request with {} parameters".format(len(data)))
        return cls(data[1])

    def encode(self):
        return yate_encode_join("%>uninstall", self.name)


class UninstallConfirm(InstallUninstallBase):
    def __init__(self, priority, name, success):
        self.msg_type = "uninstall"
        self.priority = priority
        self.name = name
        self.success = success

    def encode(self):
        return yate_encode_join("%<uninstall", str(self.priority), self.name, str(self.success).lower())


class WatchRequest:
    def __init__(self, name):
        self.name = name

    @classmethod
    def parse(cls, data):
        if len(data) != 2:
            raise YateMessageParsingError("Invalid watch request with {} parameters".format(len(data)))
        return cls(data[1])

    def encode(self):
        return yate_encode_join("%>watch", self.name)


class WatchConfirm:
    @classmethod
    def parse(cls, data):
        if len(data) < 3:
            raise YateMessageParsingError("Invalid watch from yate with only {} parameters".format(len(data)))
        name = data[1]
        success = data[2].lower() == "true"
        return cls(name, success)

    def __init__(self, name, success):
        self.msg_type = "watch"
        self.name = name
        self.success = success

    def encode(self):
        return yate_encode_join("%<watch", self.name, str(self.success).lower())


class UnwatchRequest:
    def __init__(self, name):
        self.name = name

    @classmethod
    def parse(cls, data):
        if len(data) != 2:
            raise YateMessageParsingError("Invalid unwatch request with {} parameters".format(len(data)))
        return cls(data[1])

    def encode(self):
        return yate_encode_join("%>unwatch", self.name)


class UnwatchConfirm:
    @classmethod
    def parse(cls, data):
        if len(data) < 3:
            raise YateMessageParsingError("Invalid unwatch from yate with only {} parameters".format(len(data)))
        name = data[1]
        success = data[2].lower() == "true"
        return cls(name, success)

    def __init__(self, name, success):
        self.msg_type = "unwatch"
        self.name = name
        self.success = success

    def encode(self):
        return yate_encode_join("%<unwatch", self.name, str(self.success).lower())


class ConnectToYate:
    def __init__(self, role="global", id=None, type=None):
        self.role = role
        self.id = id
        self.type = type

    def encode(self):
        params = [self.role]
        if self.id is not None:
            params.append(self.id)
            if self.type is not None:
                params.append(self.type)
        return yate_encode_join("%>connect", *params)


_yate_message_type_table = {
    "%>message": Message,
    "%<message": Message,
    "%>install": InstallRequest,
    "%<install": InstallConfirm,
    "%>uninstall": UninstallRequest,
    "%<uninstall": UninstallConfirm,
    "%>watch": WatchRequest,
    "%<watch": WatchConfirm,
    "%>unwatch": UnwatchRequest,
    "%<unwatch": UnwatchConfirm,
}
