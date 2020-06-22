import socket
from threading import Thread
import json #2.0.9
import configparser
import os
from DatabaseServer import KnowMoreDB

class SlaveServer(Thread):

    def __init__(self):
        Thread.__init__(self)

        configObject = configparser.ConfigParser()
        thisfolder = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(thisfolder, 'conf.ini')
        configObject.read(path)
        self.slaveServerIP = configObject.get('configuration','slave-server-ip')
        self.slaveServerPort = int(configObject.get('configuration','slave-server-port'))
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.slaveServerIP, self.slaveServerPort))


    def recvall(self, sock):
        data=b""
        while True:
                dataChunk = sock.recv(4096)
                data+=dataChunk   
                if dataChunk.endswith(b"\n"):
                    data = data[:-1]
                    break
        return data


    def run(self):
        while True:
            self.server.listen(1)
            clientSock, clientAddress = self.server.accept()
            data = clientSock.recv(256).decode()
            
            if data:
                clientSock.send("ALIVE".encode())

                data = self.recvall(clientSock).decode()
                data = json.loads(data)

                print("SERVED",data["ip"])

                if data["operation"]=="SEARCH":
                    db = KnowMoreDB()
                    content = data["data"]
                    query = content["query"]
                    email = content["email"]
                    pwd = content['pwd']

                    docs = db.searchDocs(email,pwd,query)

                    if docs!=None:
                        response = dict()
                        for i in range(len(docs)):
                            doc = docs[i]
                            response[i] = (doc[0], doc[1])

                        response = json.dumps(response)+"\n"
                        clientSock.send(response.encode())
                    else:
                        clientSock.send("NO_DOCS_FOUND\n".encode())

                    db.close()

                elif data["operation"]=="ADD":
                    db = KnowMoreDB()
                    content = data["data"]
                    url = content["url"]
                    text = content["text"]
                    email = content["email"]
                    pwd = content['pwd']

                    x = db.getUserRecord(email, pwd)
                    if x==None:
                        db.close()
                        clientSock.send("NO_USER_FOUND\n".encode())
                    else:
                        db.addDoc(email, pwd, url, text)
                        db.close()
                        clientSock.send("SUCCESSFULLY_ADDED\n".encode())
                

class RegisterServer(Thread):

    def __init__(self):
        Thread.__init__(self)
        configObject = configparser.ConfigParser()
        thisfolder = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(thisfolder, 'conf.ini')
        configObject.read(path)
        self.masterServerIP = configObject.get('configuration','master-server-ip')
        self.masterServerPort = int(configObject.get('configuration','master-server-port'))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.masterServerIP, self.masterServerPort))
        self.identity = configObject.get('configuration','slave-server-identity')
        self.port = int(configObject.get('configuration','slave-server-port'))


    def run(self):
        msg = self.identity +" "+str(self.port)
        self.sock.send(msg.encode())
        reply = self.sock.recv(256).decode()
        
        if reply=="SETUP_SUCCESSFUL":
            print("SETUP SUCCESSFUL!\n")
        else:
            print("SETUP FAILED!")
        self.sock.close()


setup = RegisterServer()
setup.start()

server = SlaveServer()
server.start()

