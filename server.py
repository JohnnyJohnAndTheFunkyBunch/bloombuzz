import time
import struct
import socket
import hashlib
import base64
import sys
from select import select
import re
import logging
from threading import Thread
import signal
import pycurl,json
 
# Simple WebSocket server implementation. Handshakes with the client then echos back everything
# that is received. Has no dependencies (doesn't require Twisted etc) and works with the RFC6455
# version of WebSockets. Tested with FireFox 16, though should work with the latest versions of
# IE, Chrome etc.
 
# Constants
MAGIC_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
TEXT = 0x01
BINARY = 0x02


 
 
# WebSocket implementation
class WebSocket(object):
 
    handshake = (
        "HTTP/1.1 101 Web Socket Protocol Handshake\r\n"
        "Upgrade: WebSocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: %(acceptstring)s\r\n"
        "Server: TestTest\r\n"
        "Access-Control-Allow-Origin: http://localhost\r\n"
        "Access-Control-Allow-Credentials: true\r\n"
        "\r\n"
    )
 
 
    # Constructor
    def __init__(self, client, server):
        self.client = client
        self.server = server
        self.handshaken = False
        self.header = ""
        self.data = ""
 
 
    # Serve this client
    def feed(self, data):
    
        # If we haven't handshaken yet
        if not self.handshaken:
            logging.debug("No handshake yet")
            self.header += data
            if self.header.find('\r\n\r\n') != -1:
                parts = self.header.split('\r\n\r\n', 1)
                self.header = parts[0]
                if self.dohandshake(self.header, parts[1]):
                    logging.info("Handshake successful")
                    self.handshaken = True
 
        # We have handshaken
        else:
            logging.debug("Handshake is complete")
            
            # Decode the data that we received according to section 5 of RFC6455
            recv = self.decodeCharArray(data)
            
            # Send our reply
            handleData(self,recv)
 
 
    # Stolen from http://www.cs.rpi.edu/~goldsd/docs/spring2012-csci4220/websocket-py.txt
    def sendMessage(self, s):
        """
        Encode and send a WebSocket message
        """
 
        # Empty message to start with
        message = ""
        
        # always send an entire message as one frame (fin)
        b1 = 0x80
 
        # in Python 2, strs are bytes and unicodes are strings
        if type(s) == unicode:
            b1 |= TEXT
            payload = s.encode("UTF8")
            
        elif type(s) == str:
            b1 |= TEXT
            payload = s
 
        # Append 'FIN' flag to the message
        message += chr(b1)
 
        # never mask frames from the server to the client
        b2 = 0
        
        # How long is our payload?
        length = len(payload)
        if length < 126:
            b2 |= length
            message += chr(b2)
        
        elif length < (2 ** 16) - 1:
            b2 |= 126
            message += chr(b2)
            l = struct.pack(">H", length)
            message += l
        
        else:
            l = struct.pack(">Q", length)
            b2 |= 127
            message += chr(b2)
            message += l
 
        # Append payload to message
        message += payload
 
        # Send to the client
        self.client.send(str(message))
 
 
    # Stolen from http://stackoverflow.com/questions/8125507/how-can-i-send-and-receive-websocket-messages-on-the-server-side
    def decodeCharArray(self, stringStreamIn):
    
        # Turn string values into opererable numeric byte values
        byteArray = [ord(character) for character in stringStreamIn]
        datalength = byteArray[1] & 127
        indexFirstMask = 2
 
        if datalength == 126:
            indexFirstMask = 4
        elif datalength == 127:
            indexFirstMask = 10
 
        # Extract masks
        masks = [m for m in byteArray[indexFirstMask : indexFirstMask+4]]
        indexFirstDataByte = indexFirstMask + 4
        
        # List of decoded characters
        decodedChars = []
        i = indexFirstDataByte
        j = 0
        
        # Loop through each byte that was received
        while i < len(byteArray):
        
            # Unmask this byte and add to the decoded buffer
            decodedChars.append( chr(byteArray[i] ^ masks[j % 4]) )
            i += 1
            j += 1
 
        # Return the decoded string
        return decodedChars
 
 
    # Handshake with this client
    def dohandshake(self, header, key=None):
    
        logging.debug("Begin handshake: %s" % header)
        
        # Get the handshake template
        handshake = self.handshake
        
        # Step through each header
        for line in header.split('\r\n')[1:]:
            name, value = line.split(': ', 1)
            
            # If this is the key
            if name.lower() == "sec-websocket-key":
            
                # Append the standard GUID and get digest
                combined = value + MAGIC_GUID
                response = base64.b64encode(hashlib.sha1(combined).digest())
                
                # Replace the placeholder in the handshake response
                handshake = handshake % { 'acceptstring' : response }
 
        logging.debug("Sending handshake %s" % handshake)
        self.client.send(handshake)
        return True
 
    def onmessage(self, data):
        logging.info("Got message: %s" % data)
        self.send(data)
 
    def send(self, data):
        logging.info("Sent message: %s" % data)
        self.sendMessage(data)
 
    def close(self):
        self.client.close()

 
# WebSocket server implementation
class WebSocketServer(object):
 
    # Constructor
    def __init__(self, bind, port, cls):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((bind, port))
        self.bind = bind
        self.port = port
        self.cls = cls
        self.connections = {}
        self.listeners = [self.socket]
 
    # Listen for requests
    def listen(self, backlog=5):
 
        self.socket.listen(backlog)
        logging.info("Listening on %s" % self.port)
 
        # Keep serving requests
        self.running = True
        while self.running:
        
            # Find clients that need servicing
            rList, wList, xList = select(self.listeners, [], self.listeners, 1)
            for ready in rList:
                if ready == self.socket:
                    logging.debug("New client connection")
                    client, address = self.socket.accept()
                    fileno = client.fileno()
                    self.listeners.append(fileno)
                    self.connections[fileno] = self.cls(client, self)
                else:
                    logging.debug("Client ready for reading %s" % ready)
                    client = self.connections[ready].client
                    data = client.recv(4096)
                    fileno = client.fileno()
                    if data:
                        self.connections[fileno].feed(data)
                    else:
                        logging.debug("Closing client %s" % ready)
                        self.connections[fileno].close()
                        del self.connections[fileno]
                        self.listeners.remove(ready)
            
            # Step though and delete broken connections
            for failed in xList:
                if failed == self.socket:
                    logging.error("Socket broke")
                    for fileno, conn in self.connections:
                        conn.close()
                    self.running = False

############# BLOOMBERG ##################
import blpapi
## List of monitored Stocks
STOCKS = []
LIST_OF_STOCKWATCH = []
SUBSCRIPTIONS = blpapi.SubscriptionList()
SESSION = None
SUBSCRIBED = False
KEY_CONN_DICT = {}
# key to connections[]


class StockWatch:
    def __init__(self, key, stock_name, above_or_below, price):
        self.key = key
        self.stock_name = stock_name
        self.above_or_below = above_or_below
        self.price = price
        self.triggered = False
        self.myId = stock_name + str(above_or_below) + str(int(price*100))
        print(self.myId)

def eventLoop ():
    global KEY_CONN_DICT
    lpStr = "LAST_PRICE = "
    tickerStr = "PARSEKEYABLE_DESCRIPTION_RT = \""
    while (True):
        event = SESSION.nextEvent()
        for msg in event:
            msgStr = str(msg)
            pos = msgStr.find(lpStr)
            if pos == -1:
                continue
            pos2 = msgStr[pos+len(lpStr):].find(".")
            last_price = float(msgStr[pos+len(lpStr):pos2 + pos+len(lpStr) + 3])
            print last_price
            pos = msgStr.find(tickerStr)
            if pos == -1:
                continue
            pos2 = msgStr[pos+len(tickerStr):].find(" US Equity")
            stock_name = msgStr[pos+len(tickerStr):pos2 + pos+len(tickerStr)]
            print stock_name
            for a in LIST_OF_STOCKWATCH:
                if a.stock_name == stock_name:
                    if a.above_or_below == 1: # above
                        if a.price < last_price:
                            if (not a.triggered):
                                print "send trigger"
                                sendTrigger(a.key, "Price of " + stock_name+ " above " + str(a.price) + ". Currently at " + str(last_price))
                                conn_array = KEY_CONN_DICT.get(a.key, [])
                                for c in conn_array:
                                    try:
                                        c.sendMessage("trg," + a.myId)
                                    except:
                                        conn_array.remove(c)
                                # sendWebSocketTrigger
                                a.triggered = True
                    elif a.above_or_below == -1: # below
                        if a.price > last_price:
                            if (not a.triggered):
                                print "send trigger"
                                sendTrigger(a.key, "Price of " + stock_name+ " below " + str(a.price) + ". Currently at " + str(last_price))
                                # sendWebSocketTrigger
                                conn_array = KEY_CONN_DICT.get(a.key, [])
                                for c in conn_array:
                                    try: 
                                        c.sendMessage("trg," + a.myId)
                                    except:
                                        conn_array.remove(c)
                                a.triggered = True

        
def handleStock(stock_name):
    global SUBSCRIPTIONS
    global SESSION
    global SUBSCRIBED
    #if CORRELATION:
    #    SUBSCRIPTIONS.add(stock_name+" US EQUITY")
    #else:
    SUBSCRIPTIONS.add(stock_name+" US Equity", "LAST_PRICE","",blpapi.CorrelationId(1))
    if SUBSCRIBED:
        SESSION.resubscribe(SUBSCRIPTIONS)
    else:
        SESSION.subscribe(SUBSCRIPTIONS)
        SUBSCRIBED = True

############ PAGE TRIGGER #############
def sendTrigger(key, description):
    pageduty_url = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"
    data = json.dumps({"service_key": key,\
          "incident_key": "srv01/HTTP",\
          "event_type": "trigger",\
          "description": description,\
        })

    c = pycurl.Curl()
    c.setopt(pycurl.URL, pageduty_url)
    c.setopt(pycurl.HTTPHEADER, ['Content-type: application/json'])
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDS, data)
    c.perform()

def sendResolved(key):
    pageduty_url = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"
    data = json.dumps({"service_key": key,\
          "incident_key": "srv01/HTTP",\
          "event_type": "resolve",\
        })

    c = pycurl.Curl()
    c.setopt(pycurl.URL, pageduty_url)
    c.setopt(pycurl.HTTPHEADER, ['Content-type: application/json'])
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDS, data)
    c.perform()

def sendAck(key):
    pageduty_url = "https://events.pagerduty.com/generic/2010-04-15/create_event.json"
    data = json.dumps({"service_key": key,\
          "incident_key": "srv01/HTTP",\
          "event_type": "acknowledge",\
        })

    c = pycurl.Curl()
    c.setopt(pycurl.URL, pageduty_url)
    c.setopt(pycurl.HTTPHEADER, ['Content-type: application/json'])
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDS, data)
    c.perform()
#def sendAck
############# WEB SOCKET ############

def handleData(conn,data):
    global STOCKS
    global LIST_OF_STOCKWATCH
    global KEY_CONN_DICT
    data_str = ''.join(data)
    data_arr = data_str.split(',')
    msg_type = data_arr[0] #ack or set
    if (msg_type == "set"):
        key = data_arr[1]
        stock_name = data_arr[2]
        above_or_below = int(data_arr[3])
        price = float(data_arr[4])
        print "Handling Stock " + stock_name
        stock_thread = Thread(target=handleStock, args=(stock_name,))
        stock_thread.daemon = True
        stock_thread.start()
        STOCKS.append(stock_name)
        a = StockWatch(key, stock_name, above_or_below, price)
        LIST_OF_STOCKWATCH.append(a)
        print "Adding " + a.myId
    elif (msg_type == "res"):
        key = data_arr[1]
        myId = data_arr[2]
        for a in LIST_OF_STOCKWATCH:
            if (a.key == key and a.myId == myId):
                a.triggered = False
                print "Resolving " + a.myId
                sendResolved(key)
    elif (msg_type == "ack"):
        key = data_arr[1]
        myId = data_arr[2]
        for a in LIST_OF_STOCKWATCH:
            if (a.key == key and a.myId == myId):
                a.triggered = False
                print "Ack " + a.myId
                sendAck(key)
    elif (msg_type == "del"):
        key = data_arr[1]
        myId = data_arr[2]
        for a in LIST_OF_STOCKWATCH:
            if (a.key == key and a.myId == myId):
                LIST_OF_STOCKWATCH.remove(a)
                print "Deleting " + a.myId
                sendResolved(key)
    elif (msg_type == "key"):
        key = data_arr[1]
        conn_array = KEY_CONN_DICT.get(key, [])
        conn_array.append(conn)
        KEY_CONN_DICT[key] = conn_array
        print KEY_CONN_DICT
        for a in LIST_OF_STOCKWATCH:
            if a.key == key:
                trigStr = ""
                if a.triggered:
                    trigStr = "1"
                else :
                    trigStr = "0"
                conn.sendMessage("set,"+a.stock_name+","+str(a.above_or_below)+","+'%.2f' % a.price+","+trigStr)
                # send message

        # send all stock Watcher

class BloomServer(WebSocket):
    def onmessage(self, data):
        self.send(data)
        return

if __name__ == "__main__":
    sessionOptions = blpapi.SessionOptions()
    sessionOptions.setServerHost("10.8.8.1")
    sessionOptions.setServerPort(8194)
    session = blpapi.Session(sessionOptions)
    session.start()
    session.openService("//blp/mktdata")
    SESSION = session
    event_thread = Thread(target=eventLoop)
    event_thread.daemon = True
    event_thread.start()
 
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
    server = WebSocketServer("0.0.0.0", 9876, BloomServer)
    server_thread = Thread(target=server.listen, args=[5])
    server_thread.daemon = True
    server_thread.start()
 
    # Add SIGINT handler for killing the threads
    def signal_handler(signal, frame):
        logging.info("Caught Ctrl+C, shutting down...")
        server.running = False
        sys.exit()
    signal.signal(signal.SIGINT, signal_handler)
 
    while True:
        time.sleep(100)
