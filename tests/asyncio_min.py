import asyncio
import sys

from yate.asyncio import YateAsync


async def main(yate: YateAsync):
    future = asyncio.get_event_loop().create_future()

    def notifyCallback(msg):
        msg.params["test"] = "yes"
        yate.answer_message(msg, True)
        future.set_result(msg.id)

    await yate.register_message_handler_async("chan.notify", notifyCallback)
    sys.stderr.write("Notify handler installed!\n")
    sys.stderr.flush()
    # now we wait for one message to be processed
    await future


y = YateAsync()
y.run(main)
