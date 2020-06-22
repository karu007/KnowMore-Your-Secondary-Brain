
from flask import * #1.1.1
from DatabaseServer import KnowMoreDB
from MasterServer import *
from threading import Thread
import configparser

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("after-login.html")

@app.route("/search", methods=['POST'])
def search():
    if request.method == "POST":

        query = request.json["query"]
        email = request.json["email"]
        pwd = request.json['pwd']
        ip = request.remote_addr

        docs = masterServer.process("SEARCH", {"query":query, "email":email, "pwd":pwd}, ip)

        if docs!="SERVER_DOWN":
            if docs=="NO_DOCS_FOUND":
                return "NO_DOCS_FOUND"
            else:
                return jsonify(docs)
        else:
            return "SERVER_DOWN"
        

@app.route("/add", methods=['POST'])
def add():
    if request.method == "POST":
        
        url = request.json["url"]
        text = request.json["text"]
        email = request.json["email"]
        pwd = request.json['pwd']
        ip = request.remote_addr

        docs = masterServer.process("ADD", {"url":url, "text":text, "email":email, "pwd":pwd}, ip)

        if docs!="SERVER_DOWN":
            if docs=="NO_USER_FOUND":
                return "NO_USER_FOUND"
            elif docs=="SUCCESSFULLY_ADDED":
                return "SUCCESSFULLY_ADDED"
        else:
            return "SERVER_DOWN"


if __name__ == "__main__":
    masterServer = MasterServer()
    s = SlaveServerSetup(masterServer)
    s.start()
    configObject = configparser.ConfigParser()
    thisfolder = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(thisfolder, 'conf.ini')
    configObject.read(path)
    flaskServerIp = configObject.get('configuration','master-server-ip')
    flaskServerPort = int(configObject.get('configuration','flask-server-port'))
    app.run(host=flaskServerIp, port=flaskServerPort, debug=False)
    
    