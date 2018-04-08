import subprocess
from subprocess import PIPE
import unittest

from yate.protocol import parse_yate_message

class TestAsyncYateProgram(unittest.TestCase):
    def test_async_yate_program(self):
        p = subprocess.Popen(["python", "./tests/asyncio_min.py"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
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

