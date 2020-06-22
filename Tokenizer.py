import re, os

class WordTokenizer():

    def __init__(self):
        thisfolder = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(thisfolder, 'stopwords.txt')
        with open(path, "r") as f:
            self.stopwords = set([line.rstrip('\n') for line in f])

    def tokenize(self, para):
        refinedWords = []
        rawWords = para.split()

        for i in range(len(rawWords)):
            word = rawWords[i]
            word = re.search("([/.-/']*[a-zA-Z])+",word)
            if word!=None:
                word = word.group()
                refinedWords.append(word.lower())

        return refinedWords
                
    def removeStopwords(self, wordList):
        words = list(filter(lambda w: w not in self.stopwords, wordList))
        return words
