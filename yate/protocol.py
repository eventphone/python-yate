

def yate_decode_bytes(byte_input):
    output = b""
    escaped = False
    for b in byte_input:
        if escaped:
            if b == ord("%"):
                output += bytes([b])
            else:
                if b < 64:
                    raise Exception("Unable to decode yate shitty bytes")
                output += bytes([(b-64)])
            escaped = False
        else:
            if b == ord("%"):
                escaped = True
            else:
                output += bytes([b])
    return output


''' Encode a sequence of bytes to be sent to yate

Args:
    byte_input (str): sequence of bytes to be encoded

'''
def yate_encode_bytes(byte_input):
    output = b""
    for b in byte_input:
        if b<32 or b == ord(":"):
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
        key, value = param.split("=",1)
        output[key] = value
    return output


def parse_yatemessage(bytes_input):
    splitted = yate_decode_split(bytes_input)
    messagetype = splitted[0]
    if messagetype == "%>message":
        id = splitted[1]
        time = splitted[2]
        name = splitted[3]
        returnvalue = splitted[4]
        params = yate_parse_keyvalue(splitted[5:])
        message = MessageFromYate(id, time, name, returnvalue, params)
        return message
        pass
    elif messagetype == "%>install":
        priority = splitted[1]
        name = splitted[2]
        success = True if splitted[3] == "true" else False
        message = InstallFromYate(priority, name, success)
        return message
        pass
    elif messagetype == "%>uninstall":
        pass
    elif messagetype == "%>watch":
        name = splitted[1]
        success = splitted[2]
        message = WatchFromYate(name, success)
        return message
        pass
    elif messagetype == "%>unwatch":
        pass
    elif messagetype == "%>setlocal":
        pass


class MessageFromYate:

    def __init__(self, id, time, name, returnvalue, params):
        self.id = id
        self.time = time
        self.name = name
        self.returnvalue = returnvalue
        self.params = params

    def encode_answer_for_yate(self, processed):
        processed = str(processed).lower()
        return yate_encode_join("%<message",
                                self.id,
                                processed,
                                "",
                                self.returnvalue,
                                *["=".join(item) for item in self.params.items()])


class InstallToYate:

    def __init__(self, prioriy, name, filtername=None, filtervalue=None):
        self._priority = str(prioriy)
        self._name = name
        self._filtername = filtername
        self._filtervalue = str(filtervalue)

    def encode(self):
        extraargs = []
        if self._filtername is not None:
            extraargs.append(self._filtername)
            if self._filtervalue is not None:
                extraargs.append(self._filtervalue)
        return yate_encode_join("%>install", self._priority, self._name, *extraargs)


class InstallFromYate:
    def __init__(self, priority, name, success):
        self.priority = priority
        self.name = name
        self.success = success


class WatchFromYate:

    def __init__(self, name, success):
        self._name = name
        self._success = success