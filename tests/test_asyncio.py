from subprocess import PIPE
import asyncio
import os
import subprocess
import unittest

from yate.asyncio import YateAsync
from yate.protocol import parse_yate_message, Message, MessageRequest

class TestAsyncYateProgram(unittest.TestCase):
    def test_async_yate_program(self):
        this_dir = os.path.dirname(__file__)
        test_script = os.path.join(this_dir, "asyncio_min.py")
        p = subprocess.Popen(["python3", test_script], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        install_message = p.stdout.readline().strip()
        self.assertEqual(b"%%>install:100:chan.notify", install_message)
        p.stdin.write(b"%%<install:100:chan.notify:true\n")
        p.stdin.flush()
        ready_note = p.stderr.readline().strip()
        self.assertEqual(b"Notify handler installed!", ready_note)
        print("Sending message...")
        p.stdin.write(b"%%>message:ID-42:4711:chan.notify:ret:channel=dump/3\n")
        p.stdin.flush()
        # wait for response
        response = p.stdout.readline().strip()
        msg = parse_yate_message(response)
        self.assertEqual("chan.notify", msg.name)
        self.assertEqual("ret", msg.return_value)
        self.assertEqual("ID-42", msg.id)
        self.assertEqual(msg.params, {"channel": "dump/3", "test": "yes"})
        p.wait(10)
        p.stdin.close()
        p.stdout.close()
        p.stderr.close()


class TestAsyncMessageHandling(unittest.TestCase):
    def test_async_message_processing(self):
        y = YateAsync()
        self.complete = False

        def answer_message(msg_bytes):
            msg = parse_yate_message(msg_bytes)
            if isinstance(msg, Message):
                msg.return_value = "gotIt"
                answer = msg.encode_answer_for_yate(True)
                asyncio.get_event_loop().call_soon(y._recv_message_raw, answer)

        y._send_message_raw = answer_message

        async def async_testroutine():
            msg = MessageRequest("chan.test", {}, "blubb")
            result = await y.send_message_async(msg)
            self.assertEqual("gotIt", result.return_value)
            self.complete = True

        asyncio.run(async_testroutine())
        self.assertTrue(self.complete, "Async operation did not finish")
