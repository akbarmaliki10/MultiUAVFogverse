import asyncio
import threading
import uuid
import yaml

from fogverse import Consumer, Producer, ConsumerStorage
from flask import Flask, render_template
from flask_socketio import SocketIO
from dotenv import load_dotenv

def page_not_found(*args):
  return render_template('404.html'), 404

app = Flask(__name__)
app.register_error_handler(404, page_not_found)
socketio = SocketIO(app)
loop = None
storage = None

class MyStorage(ConsumerStorage):
    def __init__(self, loop, keep_messages=False):
        self.loop = loop
        self.message = None
        super().__init__(keep_messages)

    async def add_command(self, command):
        await self.q.put(command)
        return command

class Command(Producer):
    def __init__(self, consumer, producer_topic: str, producer_server: str, loop=None):
        self.consumer = consumer
        self.producer_topic = producer_topic
        self.producer_servers = producer_server

        Producer.__init__(self, loop=loop)

    async def receive(self):
        return await self.consumer.get()

    def _after_send(self, data):
        print('masuk after send')
        print(data)
        print(self.producer_servers)
        print(self._topic)

    def callback(record, *args, **kwargs):
        print('masuk callback, ini callback jalan kalau send nya berhasil')
        print(f'record: {record}')
        print(f'args: {args}')
        print(f'kwargs: {kwargs}')
        return record

@socketio.on("take_off")
def handle_message(message):
    task = storage.send(message)
    asyncio.run_coroutine_threadsafe(task, loop)

@app.route('/<uav_id>/')
def index(uav_id=None):
    if not uav_id:
        return page_not_found()
    return render_template('index.html')

@app.route('/')
def control_center():
    total_uav = get_total_uav()
    listUavName = []
    for i in range(total_uav):
        listUavName.append("uav_"+str(i+1))
    return render_template('control_center.html', uav_list=listUavName)

async def main(loop):
    global storage
    storage = MyStorage(loop=loop)
    command = Command(storage, "uav_command", "localhost:9092", loop=loop)
    tasks = [command.run()]
    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.close()

def run_consumer(loop):
    try:
        loop.run_until_complete(main(loop))
    finally:
        loop.close()

def get_total_uav():
    # Open the YAML file
    with open('global_config.yaml', 'r') as file:
        # Load the YAML data into a Python object
        data = yaml.safe_load(file)

    # Access the data
    return data['DRONE_TOTAL']


if __name__ == '__main__':
    load_dotenv()
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=run_consumer, args=(loop,))
    thread.start()
    socketio.run(app, debug=True, host='0.0.0.0', use_reloader=False)