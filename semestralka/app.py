from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect    
import time
import random
import math

import serial

ser = serial.Serial("/dev/ttyS0")
ser.baudrate = 9600
async_mode = None

app = Flask(__name__)

btn = ""
voltage = ""

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 


def background_thread(args):
    global voltage
    voltage = 0
    count = 0
    while True:
        if btn == 'start':
            x = float(voltage)*(255/5)
            
            ser.write(bytes(str(x), 'utf-8'))
            read_ser = ser.readline()
            read_ser = read_ser.decode('ascii').split(',')
            time.sleep(0.05)
            count += 1
            socketio.emit('my_response',
                          {'data': read_ser, 'count': count},
                          namespace='/test')
        else:
            x = float(voltage)*(255/5)
            ser.write(bytes(str(x), 'utf-8'))
            read_ser = ser.readline()
            time.sleep(0.05)
            
@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)
  
@socketio.on('my_event', namespace='/test')
def test_message(message):   
    global voltage
    voltage = str(message['value'])
    
 
@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    emit('my_response', {'data': 'Connected', 'count': 0})
    
@socketio.on('click_start', namespace='/test')
def start(message):
    global btn
    btn = message['value']
    
@socketio.on('click_stop', namespace='/test')
def stop(message):
    global btn
    btn = message['value']

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)
    
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
