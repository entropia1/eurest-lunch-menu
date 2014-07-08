# -*- coding: utf-8 -*-
from StringIO import StringIO
import locale
import time
import datetime
import inspect
import csv
import calendar
import re
import sys
import os
import urllib2
from lunchinator import log_debug, log_exception
import codecs
import contextlib
import json

class LunchMenu (object):    
    def __init__(self):
        self.lunchDate = None
        self.contents = {}
    
    def isValid(self):
        return self.lunchDate != None and self.contents != None and len(self.contents) > 0
    
    def __str__(self):
        return "%s" % (self.contents)
    
    # TODO maybe add compatible locales (e.g. de_CH) 
    supportedLocales = ["de_DE", "de", "en_US"]
    fallbackLocale = "en_US"
    defaultLocaleString = None
    
    _url = None
    _messages = None
    _toggleMessages = None
    
    _lunchMenus = None
    _toggleLunchMenus= None
    _allLunchMenus = None
    
    _additives = None
    _toggleAdditives = None
    
    _lastUpdate = None
    
    @classmethod
    def _checkOutdated(cls):
        now = datetime.datetime.now()
        td = now - cls._lastUpdate
        difference = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
        if cls._lastUpdate == None or difference > 60*60:
            cls.initialize()
    
    @classmethod
    def lunchMenus(cls):
        cls._checkOutdated()
        return cls._lunchMenus
    
    @classmethod
    def toggleLunchMenus(cls):
        cls._checkOutdated()
        return cls._toggleLunchMenus
    
    @classmethod
    def allLunchMenus(cls):
        cls._checkOutdated()
        return cls._allLunchMenus

    @classmethod
    def messages(cls):
        cls._checkOutdated()
        return cls._messages
    
    @classmethod
    def toggleMessages(cls):
        cls._checkOutdated()
        return cls._toggleMessages
    
    @classmethod
    def additives(cls):
        return cls._additives
    
    @classmethod
    def toggleAdditives(cls):
        return cls._toggleAdditives
    
    @classmethod
    def getEnglishMenus(cls):
        return cls.lunchMenus() if "en" in cls.defaultLocaleString else cls.toggleLunchMenus()
    
    @classmethod
    def getGermanMenus(cls):
        return cls.lunchMenus() if "de" in cls.defaultLocaleString else cls.toggleLunchMenus()
    
    @classmethod
    def getEnglishMessages(cls):
        return cls.messages() if "en" in cls.defaultLocaleString else cls.toggleMessages()
    
    @classmethod
    def getGermanMessages(cls):
        return cls.messages() if "de" in cls.defaultLocaleString else cls.toggleMessages()

    @classmethod
    def getEnglishWeekdays(cls):
        cls._checkOutdated()
        englishMessages = cls.getEnglishMessages()
        return [englishMessages['monday'], englishMessages['tuesday'], englishMessages['wednesday'], englishMessages['thursday'], englishMessages['friday']]

    @classmethod
    def getMessages(cls, localeString):
        return cls.getGermanMessages() if "de" in localeString else cls.getEnglishMessages()

    @classmethod
    def getLunchMenu(cls, weekday, localeString):
        weekday = weekday % 7
        if weekday > 4:
            return None
        menus = cls.getGermanMenus() if "de" in localeString else cls.getEnglishMenus()
        return menus[weekday]
        
    @classmethod
    def initialize(cls, url=None):
        if url:
            cls._url = url
        try:
            cls.defaultLocaleString = locale.getdefaultlocale()[0]
            if not cls.defaultLocaleString in cls.supportedLocales:
                cls.defaultLocaleString = cls.fallbackLocale
        except:
            cls.defaultLocaleString = cls.fallbackLocale
        
        cls._messages = cls.loadMessagesForLocale(cls.defaultLocaleString)
        cls._toggleMessages = cls.loadMessagesForLocale(cls._messages["toggleLocale"])
        
        try:
            locale.setlocale(locale.LC_TIME, (cls.defaultLocaleString,"UTF-8"))
            cls._lunchMenus, cls._additives = cls.readLunchMenus(cls.defaultLocaleString, cls._messages)
        except Exception as e:
            log_exception(u"Error reading lunch menus")
            cls._lunchMenus = []
            for _ in range(5):
                cls._lunchMenus.append(e)
            pass
        
        try:
            locale.setlocale(locale.LC_TIME, (cls._messages['toggleLocale'],"UTF-8"))
            cls._toggleLunchMenus, cls._toggleAdditives = cls.readLunchMenus(cls._messages['toggleLocale'], cls._toggleMessages)
        except Exception as e:
            cls._toggleLunchMenus = []
            for _ in range(5):
                cls._toggleLunchMenus.append(e)
            pass
        
        try:
            locale.setlocale(locale.LC_TIME, (cls.defaultLocaleString,"UTF-8"))
        except:
            pass
        
        cls._allLunchMenus = cls._lunchMenus + cls._toggleLunchMenus
        cls._lastUpdate = datetime.datetime.now()
    
    @classmethod
    def today(cls):
        return datetime.date.today()
    
    @classmethod
    def loadMessages(cls, path):
        msgDict = {}
        with open(path, "rb") as inFile:
            tsvreader = csv.reader(inFile, delimiter='\t')
            for row in tsvreader:
                msgDict[row[0].decode("utf-8")] = row[1].decode("utf-8")
        return msgDict
    
    @classmethod
    def loadMessagesForLocale(cls, localeString):
        moduleFolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0])))
        currentLocalePath = "%s/lunch_menu_strings_%s.tsv" % (moduleFolder, localeString)
        if (os.path.isfile(currentLocalePath)):
            return cls.loadMessages(currentLocalePath)
        else:
            return cls.loadMessages("%s/lunch_menu_strings.tsv" % (moduleFolder))
    
    @classmethod
    def addListMenuContent(cls, menu, displayedKey, content):
        if displayedKey in menu.contents:
            l = menu.contents[displayedKey]
        else:
            l = []
        l.append(content)
        menu.contents[displayedKey] = l  
    
    @classmethod
    def readLunchMenus(cls, localeStr, messages):
        if not cls._url:
            return [Exception(messages[u"checkURL"])]*5
        
        lunchMenus = [None, None, None, None, None]
        localeStr = localeStr[:2]
        
        with contextlib.closing(urllib2.urlopen(cls._url)) as urlInput:
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
                            cls.addListMenuContent(menu, messages[keyBase + u"Displayed"], lineContent)
            
            lunchMenus[days.index(weekDay)] = menu
                
        return lunchMenus, additivesDict

if __name__ == '__main__':
    LunchMenu.initialize()
    for menu in LunchMenu.getGermanMenus():
        print menu.contents