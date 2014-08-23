# -*- coding: utf-8 -*-
from StringIO import StringIO
import locale, time, datetime, inspect, csv, calendar, re, sys, os, urllib2, codecs, contextlib, json

class LunchMenu(object):    
    def __init__(self):
        self.lunchDate = None
        self.contents = {}
    
    def isValid(self):
        return self.lunchDate != None and self.contents != None and len(self.contents) > 0
    
    def __str__(self):
        return "%s" % (self.contents)
    
class LunchMenus(object):
    # TODO maybe add compatible locales (e.g. de_CH) 
    supportedLocales = ["de_DE", "de", "en_US"]
    fallbackLocale = "en_US"
    defaultLocaleString = None
    
    def __init__(self, logger):
        self._logger = logger
        
        self._url = None
        self._messages = None
        self._toggleMessages = None
        
        self._lunchMenus = None
        self._toggleLunchMenus= None
        self._allLunchMenus = None
        
        self._additives = None
        self._toggleAdditives = None
        
        self._lastUpdate = None
        
    def initialize(self, url=None):
        if url:
            self._url = url
        try:
            self.defaultLocaleString = locale.getdefaultlocale()[0]
            if not self.defaultLocaleString in self.supportedLocales:
                self.defaultLocaleString = self.fallbackLocale
        except:
            self.defaultLocaleString = self.fallbackLocale
        
        self._messages = self.loadMessagesForLocale(self.defaultLocaleString)
        self._toggleMessages = self.loadMessagesForLocale(self._messages["toggleLocale"])
        
        try:
            self._lunchMenus, self._additives = self.readLunchMenus(self.defaultLocaleString, self._messages)
        except Exception as e:
            self._logger.exception(u"Error reading lunch menus")
            self._lunchMenus = []
            for _ in range(5):
                self._lunchMenus.append(e)
            pass
        
        try:
            self._toggleLunchMenus, self._toggleAdditives = self.readLunchMenus(self._messages['toggleLocale'], self._toggleMessages)
        except Exception as e:
            self._toggleLunchMenus = []
            for _ in range(5):
                self._toggleLunchMenus.append(e)
            pass
        
        self._allLunchMenus = self._lunchMenus + self._toggleLunchMenus
        self._lastUpdate = datetime.datetime.now()
    
    def _checkOutdated(self):
        now = datetime.datetime.now()
        td = now - self._lastUpdate
        difference = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
        if self._lastUpdate == None or difference > 60*60:
            self.initialize()
    
    def lunchMenus(self):
        self._checkOutdated()
        return self._lunchMenus
    
    def toggleLunchMenus(self):
        self._checkOutdated()
        return self._toggleLunchMenus
    
    def allLunchMenus(self):
        self._checkOutdated()
        return self._allLunchMenus

    def messages(self):
        self._checkOutdated()
        return self._messages
    
    def toggleMessages(self):
        self._checkOutdated()
        return self._toggleMessages
    
    def additives(self):
        return self._additives
    
    def toggleAdditives(self):
        return self._toggleAdditives
    
    def getEnglishMenus(self):
        return self.lunchMenus() if "en" in self.defaultLocaleString else self.toggleLunchMenus()
    
    def getGermanMenus(self):
        return self.lunchMenus() if "de" in self.defaultLocaleString else self.toggleLunchMenus()
    
    def getEnglishMessages(self):
        return self.messages() if "en" in self.defaultLocaleString else self.toggleMessages()
    
    def getGermanMessages(self):
        return self.messages() if "de" in self.defaultLocaleString else self.toggleMessages()

    def getEnglishWeekdays(self):
        self._checkOutdated()
        englishMessages = self.getEnglishMessages()
        return [englishMessages['monday'], englishMessages['tuesday'], englishMessages['wednesday'], englishMessages['thursday'], englishMessages['friday']]

    def getMessages(self, localeString):
        return self.getGermanMessages() if "de" in localeString else self.getEnglishMessages()

    def getLunchMenu(self, weekday, localeString):
        weekday = weekday % 7
        if weekday > 4:
            return None
        menus = self.getGermanMenus() if "de" in localeString else self.getEnglishMenus()
        return menus[weekday]
    
    def today(self):
        return datetime.date.today()
    
    def loadMessages(self, path):
        msgDict = {}
        with open(path, "rb") as inFile:
            tsvreader = csv.reader(inFile, delimiter='\t')
            for row in tsvreader:
                msgDict[row[0].decode("utf-8")] = row[1].decode("utf-8")
        return msgDict
    
    def loadMessagesForLocale(self, localeString):
        moduleFolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0])))
        currentLocalePath = "%s/lunch_menu_strings_%s.tsv" % (moduleFolder, localeString)
        if (os.path.isfile(currentLocalePath)):
            return self.loadMessages(currentLocalePath)
        else:
            return self.loadMessages("%s/lunch_menu_strings.tsv" % (moduleFolder))
    
    def addListMenuContent(self, menu, displayedKey, content):
        if displayedKey in menu.contents:
            l = menu.contents[displayedKey]
        else:
            l = []
        l.append(content)
        menu.contents[displayedKey] = l  
    
    def readLunchMenus(self, localeStr, messages):
        if not self._url:
            return [Exception(messages[u"checkURL"])]*5, {}
        
        lunchMenus = [None, None, None, None, None]
        localeStr = localeStr[:2]
        
        with contextlib.closing(urllib2.urlopen(self._url)) as urlInput:
            lunchJSON = urlInput.read()
            lunchObj = json.loads(lunchJSON)
            
        days = [u"mon", u"tue", u"wed", u"thu", u"fri"]
        
        additivesDict = {}
        for additive in lunchObj[u"settings"][u"additives"]:
            additivesDict[additive[u"id"]] = additive[u"text"][localeStr]
            
        for lunchDay in lunchObj[u"menu"]:
            menu = LunchMenu()
            
            unixDate = lunchDay[u"date"]
            weekDay = lunchDay[u"weekDay"]
            menu.lunchDate = datetime.datetime.fromtimestamp(unixDate).date()
            counters = lunchDay[u"counters"]
            for counter in counters:
                lineDesc = counter[u"title"][localeStr]
                lineDescUpper = lineDesc.upper()
                for dishDict in counter[u"dishes"]:
                    if u"additives" in dishDict:
                        additives = dishDict[u"additives"]
                    else:
                        additives = None
                        
                    if u"description" in dishDict:
                        description = dishDict[u"description"][localeStr].strip()
                        if len(description) <= 1:
                            description = None
                    else:
                        description = None
                        
                    if u"title" in dishDict:
                        title = dishDict[u"title"][localeStr].strip()
                    else:
                        title = None
                        
                    
                    for keyBase in (u'soup', u'mainDishes', u'supplements', u'desserts'):
                        if lineDescUpper.startswith(messages[keyBase + u"Source"]):
                            keyInfo = lineDesc[len(messages[keyBase + u"Source"]):].strip()
                            if len(keyInfo) <= 2:
                                # ignore numbers and affixes
                                keyInfo = None
                            elif u"(" in keyInfo and u")" in keyInfo:
                                # extract stuff in braces 
                                keyInfo = keyInfo[keyInfo.index(u"(") + 1:keyInfo.index(u")")]
                                
                            lineContent = (title, description, additives, keyInfo)
                            self.addListMenuContent(menu, messages[keyBase + u"Displayed"], lineContent)
            
            lunchMenus[days.index(weekDay)] = menu
                
        return lunchMenus, additivesDict

if __name__ == '__main__':
    from lunchinator.log import initializeLogger, getCoreLogger
    initializeLogger()
    l = LunchMenus(getCoreLogger())
    l.initialize()
    for menu in l.getGermanMenus():
        print unicode(menu)
        
        