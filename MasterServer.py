import socket
from threading import Thread
import json #2.0.9
import configparser
import os

class Server():

    def __init__(self, id, ip, port):
        super().__init__()
        self.identity = id
        self.ip = ip
        self.port = port
        self.isAlive = True


class MasterServer():

    def __init__(self):
        self.availableServers = dict()
        self.serverQueue = []
        self.turn = -1


    def getAvailableServers(self):
        print("Server Queue: ", self.serverQueue)

    
    def getServer(self):
        if len(self.serverQueue)!=0:
            self.turn = (self.turn+1)%len(self.serverQueue)

            id = self.serverQueue[self.turn]
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverObj = self.availableServers[id]

        try:
            self.sock.connect((serverObj.ip, serverObj.port))
            self.sock.send("PING".encode())
            reply = self.sock.recv(256).decode()
        except:
            reply = "DEAD"

        if reply!="ALIVE" and len(self.serverQueue)==0:
            return None

        elif reply!="ALIVE":

            del self.availableServers[id]
            del self.serverQueue[self.turn]
            self.sock.close()

            queueLen = len(self.serverQueue)

            if self.turn == queueLen and self.turn!=0:
                self.turn = 0

            elif self.turn == queueLen and self.turn==0:
                return None

            id = self.getServer()

            if id==None:
                return None
        
        return id


    def recvall(self, sock):
        data=b""
        while True:
                dataChunk = sock.recv(4096)
                data+=dataChunk   
                if dataChunk.endswith(b"\n"):
                    data = data[:-1]
                    break
        return data


    def process(self, operation, data, ipaddr):
        id = self.getServer()
        if id!=None:
            content = {"operation":operation, "data":data, "ip":ipaddr}
            content = json.dumps(content)
            content+="\n"
            self.sock.send(content.encode())

            reply = self.recvall(self.sock).decode()

            self.sock.close()

            if reply=="NO_DOCS_FOUND":
                return "NO_DOCS_FOUND"
            elif reply=="NO_USER_FOUND":
                return "NO_USER_FOUND"
            elif reply=="SUCCESSFULLY_ADDED":
                return "SUCCESSFULLY_ADDED"
            else:
                return json.loads(reply)
        else:
            if len(self.serverQueue)!=0:
                self.sock.close()
            return "SERVER_DOWN"
        

class SlaveServerSetup(Thread):
        
    def __init__(self, masterServerObj):
        Thread.__init__(self)
        configObject = configparser.ConfigParser()
        thisfolder = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(thisfolder, 'conf.ini')
        configObject.read(path)
        self.masterServerIP = configObject.get('configuration','master-server-ip')
        self.masterServerPort = int(configObject.get('configuration','master-server-port'))
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.masterServerIP, self.masterServerPort))
        self.masterServerObj = masterServerObj


    def run(self):
        while True:
            self.server.listen(5)
            clientSock, clientAddress = self.server.accept()
            data = clientSock.recv(256).decode()

            if data:
                identity = data.split()[0]
                port = data.split()[1]
                
                self.masterServerObj.availableServers[identity] = Server(identity, clientAddress[0], int(port))
                self.masterServerObj.serverQueue.append(identity)
                self.masterServerObj.getAvailableServers()
                clientSock.send("SETUP_SUCCESSFUL".encode())

                
