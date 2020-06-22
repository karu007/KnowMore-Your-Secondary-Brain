# python==3.6.5
import os
import hashlib
import pymongo #3.10.1
import math
from collections import OrderedDict
from Tokenizer import WordTokenizer
import configparser

class KnowMoreDB():
    
    def __init__(self):
        configObject = configparser.ConfigParser()
        thisfolder = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(thisfolder, 'conf.ini')
        configObject.read(path)
        dbIp = configObject.get('configuration','db-server-ip')
        dbPort = int(configObject.get('configuration','db-server-port'))
        self.conn = pymongo.MongoClient("mongodb://"+dbIp+":"+str(dbPort)+"/")
        self.db = self.conn['KnowMoreDB']
        self.collection = self.db["User-Data"]
        self.tokenizer = WordTokenizer()


    def close(self):
        self.conn.close()


    def clearCollection(self):
        self.collection.remove({})


    def addUser(self, userName, pwd, hashThePwd=False):
        userName = userName.replace("@","").replace(".","")
        if hashThePwd:
            pwd = hashlib.sha256(pwd.encode()).hexdigest()
        query = {"user-metadata.username":{"$eq":userName}}
        mongoDbCursor = self.collection.find(query)

        """ Add new user only if an account with the same username doesn't exist already. """
        if mongoDbCursor.count()==0:
            content = {"user-metadata":{"username":userName, "pwd":pwd, "nDocs":0}, "docs":{}, "search-metadata":{}}
            self.collection.insert_one(content)
            return True
        else:
            return False


    def getUserRecord(self, userName, pwd):
        userName = userName.replace("@","").replace(".","")
        query = {"user-metadata.username":userName}
        mongoDbCursor = self.collection.find(query)

        if mongoDbCursor.count()==1:
            record = mongoDbCursor[0]
            if record["user-metadata"]["pwd"]==pwd:
                return mongoDbCursor[0]
            else:
                return None
        elif mongoDbCursor.count()==0:
            return None


    def searchDocs(self, userName, pwd, query):
        userRecord = self.getUserRecord(userName, pwd)
        tokens = self.tokenizer.tokenize(query)
        tokens = self.tokenizer.removeStopwords(tokens)

        queryScore = dict()
        docScore = dict()

        for token in tokens:
            tfidfScore = queryScore.get(token, None)
            termIdf = self.idf(userRecord, token)
            if tfidfScore == None:
                queryScore[token] = termIdf
            else:
                queryScore[token]+= termIdf

            docsAndScores = docScore.get(token, None)
            if docsAndScores == None:
                docIds = userRecord["search-metadata"].get(token, None)
                if docIds==None:
                    docScore.update({token:{}})
                else:
                    docIds = docIds["tf"].keys()
                    for docId in docIds:
                        termScore = self.tf(userRecord, token, docId)*termIdf
                        
                        docScore[token] = {docId: termScore}

        """ @format:
                queryScore = {w1:2.146, w2:1.43, w3:0.12, w4:1.62} 
                docScore = {w1:{doc1: 1.32, doc3: 1.43}, w2:{doc6: 1.12, doc1: 1.98}... } """
        
        similarity = self.cosineSimilarity(queryScore, docScore)

        if similarity!=None:
            searchResults = []

            for docId, simscore in similarity.items():
                searchResults.append((userRecord["docs"][docId]["url"], userRecord["docs"][docId]["text"], simscore))

            searchResults = sorted(searchResults, key = lambda x: x[2], reverse=True)
            return searchResults
        else:
            return None


    def cosineSimilarity(self, queryScore, docScore):
        words = queryScore.keys()

        uniqueDocIds = None
        for word in words:        
            docids = docScore[word]
            if len(docids)!=0:
                uniqueDocIds = set(docids.keys())

        docVectors = dict()

        if uniqueDocIds!=None:
            for docId in uniqueDocIds:
                for word in words:
                    score = docScore[word].get(docId, None)
                    if score==None:
                        if docVectors.get(docId, None)!=None:
                            docVectors[docId].update({word:0})
                        else:
                            docVectors[docId] = {word:0}
                    else:
                        if docVectors.get(docId, None)!=None:
                            docVectors[docId].update({word:score})
                        else:
                            docVectors[docId] = {word:score}
            
            """ @format: 
                    docVectors = {docId1: {w1:1.2, w2:1.3, w3:0, w4:3.1}, 
                                docId2: {w1:0.78, w2:0.43, w3:1.94, w4:3.18}... } 
                    queryScore = {w1:2.146, w2:1.43, w3:0.12, w4:1.62} """

            docSimilarityScore = dict()

            for docId in docVectors.keys():
                product = 0
                docModulus = 0
                queryModulus = 0
                for word in words:
                    if docVectors[docId].get(word, None) != None:
                        product += (docVectors[docId][word] * queryScore[word])
                        queryModulus += (queryScore[word]**2)
                        docModulus += (docVectors[docId][word]**2)

                docModulus = docModulus**0.5
                queryModulus = queryModulus**0.5

                docSimilarityScore[docId] = product/(docModulus*queryModulus)

                """ @format:
                        docSimilarityScore = {docId1: 6.4, docId2: 1.3} """

                return docSimilarityScore
        
        else:
            return None


    def tf(self, userRecord, term, docId):
        count = userRecord["search-metadata"][term]["tf"].get(docId, None)
        if count!=None:
            """ If term and docId is present in search-metadata, then it is surely present in docs """
            nTerms = userRecord["docs"][docId]["nTerms"]
            tf = count/nTerms
            return tf
        else:
            return 0


    def idf(self, userRecord, term):
        nDocs = userRecord["user-metadata"]["nDocs"]
        word = userRecord["search-metadata"].get(term, None)
        if word!=None:
            docCount = word["globalCount"]
            idf = math.log(nDocs/docCount)
            return idf
        else:
            return 0


    def addDoc(self, userName, pwd, url, text):
        userRecord = self.getUserRecord(userName, pwd)
        if userRecord is None:
            return False

        docId = hashlib.sha256((url+text).encode()).hexdigest()
        tokens = self.tokenizer.tokenize(text)
        tokens = self.tokenizer.removeStopwords(tokens)
        nTerms = len(tokens)

        doc = userRecord["docs"].get(docId, None)
        userName = userRecord["user-metadata"]["username"]

        if doc==None:
            query = {"user-metadata.username":userName}
            content = {"$set":{"docs."+docId:{"url":url, "text":text, "nTerms":nTerms}}}
            self.collection.update_one(query, content)

            nDocs = userRecord["user-metadata"]["nDocs"]
            content = {"$set":{"user-metadata.nDocs":nDocs+1} }
            self.collection.update_one(query, content)

            tokensAndCount = dict()

            for token in tokens:
                c = tokensAndCount.get(token, None)
                if c==None:
                    tokensAndCount[token] = 1
                else:
                    tokensAndCount[token] = c+1

            for token,count in tokensAndCount.items():
                word = userRecord["search-metadata"].get(token, None)

                if word==None:
                    content = {"$set":{"search-metadata."+token:{"tf":{docId:count},"globalCount":1}}}
                    self.collection.update_one(query, content)
                else:
                    globalCount = word["globalCount"]
                    content = {"$set":{"search-metadata."+token+".tf."+docId:count, "search-metadata."+token+".globalCount":globalCount+1}}
                    self.collection.update_one(query, content)

        return True

