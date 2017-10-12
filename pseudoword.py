#!/usr/bin/python
# coding=utf-8

import random
import re
import os
import pickle
import argparse
import twython

class Markov_Step:
    def __init__(self):
        self.NextSteps = {}
        self.TotalOccurences = {}
    
    def Init_AddNextStep_Len(self, Char, CurrentLen, Value):
        if not CurrentLen in self.NextSteps: self.NextSteps[CurrentLen] = {} 
        if not Char in self.NextSteps[CurrentLen]: self.NextSteps[CurrentLen][Char] = 0 
        self.NextSteps[CurrentLen][Char] += Value
        if not CurrentLen in self.TotalOccurences: self.TotalOccurences[CurrentLen] = 0
        self.TotalOccurences[CurrentLen] += Value
                
    def Init_AddNextStep(self, Char, CurrentLen):
        if CurrentLen>=3: self.Init_AddNextStep_Len(Char, CurrentLen-2, 2)
        if CurrentLen>=2: self.Init_AddNextStep_Len(Char, CurrentLen-1, 3)
        self.Init_AddNextStep_Len(Char, CurrentLen  , 4)
        self.Init_AddNextStep_Len(Char, CurrentLen+1, 3)
        self.Init_AddNextStep_Len(Char, CurrentLen+2, 2)
                
    def Use_GetNextStep(self, CurrentLen):
        R = random.randrange(0, self.TotalOccurences[CurrentLen])
        for Char in self.NextSteps[CurrentLen]:
            NumberOccurences = self.NextSteps[CurrentLen][Char]
            if R <= NumberOccurences: return Char
            R -= NumberOccurences
        return None
    
class Markov:
    def __init__(self):
        self.Chain = {}        
        self.RealWords = {}
        self.Order = 3

    def Init_AddWord(self, Word):
        W = Word.lower() + "$"
        for I in range(0, len(W)):
            Prefix = W[:I][-self.Order:]
            NextChar = W[I]
            if not Prefix in self.Chain: self.Chain[Prefix] = Markov_Step()
            self.Chain[Prefix].Init_AddNextStep(NextChar, I)
        self.RealWords[ Word ] = None
            
    def Use_GetWord(self):
        W = ''
        I = 1
        while True:
            Prefix = W[:I][-self.Order:]
            if not Prefix in self.Chain:
                break
            Step = self.Chain[Prefix]
            NextStep  = Step.Use_GetNextStep(I)
            if NextStep == "$":
                break
            W += NextStep
            I += 1
        return W
        
    def Use_GetPseudoWord(self):
        W = ''
        while True: 
            W = self.Use_GetWord()
            if not W in self.RealWords: break
        return W

def GetWord(Count):        
    LocalDir = os.path.dirname(os.path.realpath(__file__))
    DictPath = LocalDir + '/pseudoword.dict.txt'
    ChainPath = LocalDir + '/pseudoword.chain.pkl'
    StripRE = re.compile('^(.+)\t(.+)\t(.+)$')
    
    if os.path.isfile(ChainPath):    
        with open(ChainPath, 'rb') as ChainFile:
            Chain = pickle.load(ChainFile)
    else:
        Chain = Markov()
        with open(DictPath, 'r') as DictFile:
            I = 0
            for Line in DictFile:
                if Line.startswith("#"): continue
                if len(Line) == 0: continue
                Matches = StripRE.match(Line.strip())
                Word = Matches.group(1)
                Categories = Matches.group(3)
                if len(Word) < Chain.Order: continue
                if not Word.isalpha(): continue
                if not Word.islower(): continue
                if not Categories in ['Vmn-----', 'Afpms-', 'Afpfs-','Ncms--', 'Ncfs--', 'Rgp'] : continue                
                Chain.Init_AddWord(Word)
                I+=1
            print( "{0} words added to the chain".format(I))

        with open(ChainPath, 'wb') as ChainFile:
            pickle.dump(Chain, ChainFile, pickle.HIGHEST_PROTOCOL)
        
    Result = []
    for I in range(Count): Result.append(Chain.Use_GetPseudoWord())
    return Result
    
TWIT_FORMAT = """Pseudomots du jour : \n{0}"""    
WINNER_FORMAT = """Meilleure définition : https://twitter.com/{0}/status/{1}"""    

if __name__ == "__main__":   
    
    Parser = argparse.ArgumentParser(description='Generates pseudowords.')
    Parser.add_argument('--count',                help='Number of pseudowords to generate.', type=int, default = 1)
    Parser.add_argument('--twitter-app-key',      help='Twitter app key.'                  , default = ''  )
    Parser.add_argument('--twitter-app-secret',   help='Twitter app secret.'               , default = ''  )
    Parser.add_argument('--twitter-token',        help='Twitter token.'                    , default = ''  )
    Parser.add_argument('--twitter-token-secret', help='Twitter token secret.'             , default = ''  )
    Parser.add_argument('--twitter-result',       help='Do not generate words, but promote result of latest tweet', action = 'store_const', const = True, default=False )
    Args = Parser.parse_args()
    
    TwitterAPI = None
    if Args.twitter_app_key != '':
        TwitterAPI = twython.Twython(Args.twitter_app_key, Args.twitter_app_secret, Args.twitter_token, Args.twitter_token_secret)
        User = TwitterAPI.verify_credentials()

    if Args.twitter_result and TwitterAPI != None:
        print('Get Latest tweet')
        Timeline = TwitterAPI.get_user_timeline(user_id = User['id'], count=1, trim_user=True)
        LatestTweet = Timeline[0]
        print('Load replies')
        Mentions = TwitterAPI.get_mentions_timeline(count = 200, include_entities=False)
        RepliesToLatestTweet = []
        for Mention in Mentions:
            if Mention['in_reply_to_status_id'] == LatestTweet['id']:
                RepliesToLatestTweet.append(Mention)
        print('Selecting winners')
        MaxFavs = 0
        for Tweet in RepliesToLatestTweet:
            if Tweet['favorite_count'] > MaxFavs:
                MaxFavs = Tweet['favorite_count']

        Winners = []
        for Tweet in RepliesToLatestTweet: 
            if Tweet['favorite_count'] == MaxFavs:
                Winners.append(Tweet)

        print('Twitting results')
        for Tweet in Winners:
            TwitMsg = WINNER_FORMAT.format( Tweet['user']['screen_name'], Tweet['id'])
            print(TwitMsg)
            TwitterAPI.update_status(status=TwitMsg)

    
    Words = GetWord(Args.count)
    
    if TwitterAPI != None:
        Twit_List = "\n".join(map(lambda x: '- '+x, Words))
        Twit = TWIT_FORMAT.format(Twit_List)
        print("Twitting :\n" + Twit) 
        TwitterAPI = twython.Twython(Args.twitter_app_key, Args.twitter_app_secret, Args.twitter_token, Args.twitter_token_secret)
        TwitterAPI.verify_credentials()
        TwitterAPI.update_status(status=Twit)
    else:    
        for W in Words: print(W)   
            
