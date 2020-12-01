ORD_PERCENT = ord("%")
ORD_COLON = ord(":")


def yate_decode_bytes(byte_input: bytes):
    output = b""
    view = memoryview(byte_input)
    pos = 0
    try:
        while True:
            next_percent = byte_input.find(ORD_PERCENT, pos)
            if next_percent < 0:
                return output + view[pos:]
            output += view[pos:next_percent]
            if view[next_percent+1] == ORD_PERCENT:
                output += b"%"
            else:
                output += (view[next_percent+1]-64).to_bytes(1, "big")
            pos = next_percent+2
    except IndexError:
        raise YateMessageParsingError("Received invalid yate message. Upcode without encoded character")
    except ValueError:
        raise YateMessageParsingError("Received invalid upcode: Encoded character too small")


def yate_encode_bytes(byte_input: bytes):
    output = b""
    view = memoryview(byte_input)
    pos = 0
    for i in range(len(byte_input)):
        if view[i] < 32 or view[i] == ORD_COLON:
            output += view[pos:i]
            output += b"%" + (view[i]+64).to_bytes(1, "big")
            pos = i+1
        elif view[i] == ORD_PERCENT:
            output += view[pos:i]
            output += b"%%"
            pos = i+1
    output += view[pos:]
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


class SetLocalRequest:
    def __init__(self, param, value=None):
        self.msg_type = "setlocal"
        self.param = param
        self.value = value or ""

    @classmethod
    def parse(cls, data):
        if len(data) < 2:
            raise YateMessageParsingError("Invalid setlocal request with {} parameters".format(len(data)))
        elif len(data) == 2:
            return cls(data[1])
        return cls(data[1], data[2])

    def encode(self):
        return yate_encode_join("%>setlocal", self.param, self.value)


class SetLocalAnswer:
    def __init__(self, param, value, success):
        self.msg_type = "setlocal"
        self.param = param
        self.value = value
        self.success = success

    @classmethod
    def parse(cls, data):
        if len(data) != 4:
            raise YateMessageParsingError("Invalid setlocal answer with {} parameters".format(len(data)))
        success = data[3].lower() == "true"
        return cls(data[1], data[2], success)

    def encode(self):
        return yate_encode_join("%<setlocal", self.param, self.value, str(self.success).lower())


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
    "%>setlocal": SetLocalRequest,
    "%<setlocal": SetLocalAnswer,
}
