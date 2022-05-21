from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect    
import time
import random
import math
import MySQLdb
import configparser as ConfigParser
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


config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print(myhost)

def background_thread(args):
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
    dataList = [] 
    global voltage
    voltage = 0
    count = 0
    dataCounter = 0
    while True:
        if btn == 'start':
            x = float(voltage)*(255/5)
            
            ser.write(bytes(str(x), 'utf-8'))
            read_ser = ser.readline()
            read_ser = read_ser.decode('ascii').split(',')
            
            time.sleep(0.05)
            
            read_ser_sent = read_ser[0]
            read_ser_sent = read_ser_sent.strip("\r\n")
            read_ser_sent = float(read_ser_sent)
            
            dataDict = {
            "x": dataCounter,
            "y": read_ser_sent,
            "voltage": float(voltage)}
            dataList.append(dataDict)
            dataCounter += 1
            
            count += 1
            socketio.emit('my_response',
                          {'data': read_ser_sent, 'count': count},
                          namespace='/test')
        if btn == 'stop':
            if len(dataList)>0:
                print(str(dataList))
                fuj = str(dataList).replace("'", "\"")
                
                write2file(fuj)
                
                cursor = db.cursor()
                cursor.execute("SELECT MAX(id) FROM voltage")
                maxid = cursor.fetchone()
                cursor.execute("INSERT INTO voltage (id, value) VALUES (%s, %s)", (maxid[0] + 1, fuj))
                db.commit()
            dataList = []
            dataCounter = 0
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
    
@app.route('/db')
def db():
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  cursor.execute('''SELECT  hodnoty FROM  graph WHERE id=1''')
  rv = cursor.fetchall()
  return str(rv)    

@app.route('/dbdata/<string:num>', methods=['GET', 'POST'])
def dbdata(num):
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  print(num)
  cursor.execute("SELECT hodnoty FROM  graph WHERE id=%s", num)
  rv = cursor.fetchone()
  return str(rv[0])
   
@socketio.on('db_event', namespace='/test')
def db_message(message):   
#    session['receive_count'] = session.get('receive_count', 0) + 1 
    session['db_value'] = message['value']    
#    emit('my_response',
#         {'data': message['value'], 'count': session['receive_count']})

@app.route('/write')
def write2file(fuj):
    fo = open("static/files/data.txt","a+")    
    val = fuj
    fo.write("%s\r\n" %val)
    return "done"

@app.route('/read/<string:num>')
def readmyfile(num):
    fo = open("static/files/test.txt","r")
    rows = fo.readlines()
    return rows[int(num)-1]

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)
    
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
