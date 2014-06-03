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
    
    _messages = None
    _toggleMessages = None
    
    _lunchMenus = None
    _toggleLunchMenus= None
    _allLunchMenus = None
    
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
    def initialize(cls):
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
            cls._lunchMenus = cls.readLunchMenus(cls._messages['lunchMenuURL'], cls._messages)
        except Exception as e:
            log_exception(u"Error reading lunch menus")
            cls._lunchMenus = []
            for _ in range(5):
                cls._lunchMenus.append(e)
            pass
        
        try:
            locale.setlocale(locale.LC_TIME, (cls._messages['toggleLocale'],"UTF-8"))
            cls._toggleLunchMenus = cls.readLunchMenus(cls._toggleMessages['lunchMenuURL'], cls._toggleMessages)
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
    def handleCommaSeparatedValues(cls, lineContent):
        array = []
        begin = 0
        braceLevel = 0
        inBraceBegin = 0
        isSupplementsBrace = False
        for i in range(len(lineContent)):
            if lineContent[i] == ',':
                if braceLevel == 0:
                    aValue = lineContent[begin:i].strip()
                    if (len(aValue) > 0):
                        array.append(lineContent[begin:i].strip())
                    begin = i + 1
                else:
                    if len(lineContent[inBraceBegin:i].strip()) > 2:
                        isSupplementsBrace = False
                    inBraceBegin = i + 1
            elif lineContent[i] == '(':
                braceLevel = braceLevel + 1
                if braceLevel == 1:
                    inBraceBegin = i + 1
                    isSupplementsBrace = True
            elif lineContent[i] == ')':
                braceLevel = braceLevel - 1
                if braceLevel == 0 and isSupplementsBrace:
                    array.append(lineContent[begin:i + 1].strip())
                    begin = i + 1
        
        lastElement = lineContent[begin:].strip()
        if len(lastElement) > 0:
            array.append(lastElement)
            
        if array[-1].strip().endswith(","):
            array[-1] = array[-1][:array[-1].rfind(",")]
        return array

    @classmethod
    def extract(cls, text, start, current):
        # TODO until current or current + 1?
        return text[start:current].strip()
    
    @classmethod
    def findAdditives(cls, plainText):
        additives = {}
        additiveStart = 0
        braceLevel = 0
        index = 0
        while index < len(plainText):
            curChar = plainText[index]
            if curChar == u',':
                if braceLevel > 0:
                    additive = cls.extract(plainText, additiveStart, index)
                    if len(additive) <= 2:
                        for j in range(additiveStart, index):
                            additives[j] = additive
                    additiveStart = index + 1
            elif curChar in (u' ', u'\t'):
                additiveStart = additiveStart + 1
            elif curChar == u'(':
                braceLevel = braceLevel + 1
                additiveStart = index + 1
            elif curChar == u')':
                braceLevel = braceLevel - 1
                additive = cls.extract(plainText, additiveStart, index).strip()
                if len(additive) <= 2:
                    for j in range(additiveStart, index):
                        additives[j] = additive
            index = index + 1
        return additives
    
    @classmethod
    def extractAdditives(cls, line):
        additives = ""
        addStart = cls.additivesStart(line)
        if addStart >= 0:
            additives = line[addStart + 1:-1].strip()
            line = line[:addStart].strip()
            
        return (line, additives)
    
    @classmethod
    def additivesStart(cls, line):
        globalStart = -1
        additiveStart = 0
        braceLevel = 0
        for i in range(len(line)):
            curChar = line[i]
            if curChar == ',':
                if braceLevel > 0:
                    additive = line[additiveStart:i].strip()
                    if len(additive) <= 2:
                        return globalStart
                    additiveStart = i + 1
            elif curChar in (' ', '\t'):
                additiveStart = additiveStart + 1
            elif curChar == '(':
                braceLevel = braceLevel + 1
                if braceLevel == 1:
                    globalStart = i
                additiveStart = i + 1
            elif curChar == ')':
                braceLevel = braceLevel - 1
                additive = line[additiveStart:i].strip()
                if len(additive) <= 2:
                    for _j in range(additiveStart, i):
                        return globalStart
        return -1
    
    @classmethod
    def handleLine(cls, menu, lineDesc, lineContent, lastKey, messages):
        if lineDesc == messages['soupSource']:
            menu.contents[messages['soupDisplayed']] = lineContent
            return False
        elif lineDesc in (messages['mainDishesSource'], messages['mainDishesOrSource']):
            mainDishes = None
            if messages['mainDishesDisplayed'] in menu.contents:
                mainDishes = menu.contents[messages['mainDishesDisplayed']]
            else:
                mainDishes = []
            mainDishes.append(lineContent)
            menu.contents[messages['mainDishesDisplayed']] = mainDishes
            return messages['mainDishesDisplayed']
        elif lineDesc == messages['supplementsSource']:
            supplements = cls.handleCommaSeparatedValues(lineContent)
            menu.contents[messages['supplementsDisplayed']] = supplements
            return messages['supplementsDisplayed']
        elif lineDesc == messages['dessertsSource']:
            desserts = cls.handleCommaSeparatedValues(lineContent)
            menu.contents[messages['dessertsDisplayed']] = desserts
            return messages['dessertsDisplayed']
        else:
            log_debug("Unknown key: %s, append to last list" % lineDesc)
            if lastKey == None:
                return None
            lastValue = menu.contents[lastKey]
            if type(lastValue) == list:
                isFirst = True
                for aValue in cls.handleCommaSeparatedValues(lineContent):
                    # check if last value of list is finished (has additives)
                    if isFirst and cls.additivesStart(lastValue[-1]) == -1:
                        lastValue[-1] = "%s %s" % (lastValue[-1], aValue)
                    else:
                        lastValue.append(aValue)
                    isFirst = False
            return lastKey
        return lineDesc
        
    @classmethod
    def isSeparatorLine(cls, line):
        return line.startswith("***")
    
    @classmethod
    def ignoreLine(cls, line):
        return len(line) == 0 or cls.isSeparatorLine(line)
    
    @classmethod
    def addMenu(cls, thisMenu, lunchMenus):
        if thisMenu.lunchDate != None:
            if thisMenu.lunchDate.weekday() > 4:
                log_debug("WTF lunch on weekend!?")
            lunchMenus[thisMenu.lunchDate.weekday()] = thisMenu
    
    @classmethod
    def checkDate(cls, dateString, messages):
        aDate = None
        while len(dateString) > 0:
            try:
                aDate = datetime.datetime.strptime(dateString, messages['dateFormatSource'])
                break
            except:
                try:
                    aDate = datetime.datetime.strptime(dateString, messages['dateFormatSource2'])
                    break
                except:
                    dateString = ' '.join(dateString.split()[:-1])
        if len(dateString) == 0:
            raise Exception("Cannot parse.")
            
        aDate = aDate.replace(datetime.date.fromtimestamp(time.time()).year, aDate.month, aDate.day).date()
        
        weekdayString = datetime.datetime.combine(aDate, datetime.time()).strftime("%A")
        if not dateString.startswith(weekdayString):
            # Someone mistyped the date again...
            # Use the Week day string, put it into current week
            weekdayString = dateString[:dateString.find(messages['weekdaySeparator'])]
            weekday = list(calendar.day_name).index(weekdayString)
            
            today = cls.today()
            theDay = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(days=weekday)
            theDay = theDay.replace(theDay.year, theDay.month, theDay.day, 0, 0, 0, 0)
            
            return theDay
        
        return aDate
    
    @classmethod
    def readLunchMenus(cls, url, messages):
        lunchMenus = [None, None, None, None, None]
        
        proxy_handler = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_handler)                
        with contextlib.closing(opener.open(url)) as u:
            txt = u.read().decode('cp1252')
    
        lunchFile = StringIO(txt)
                
        try:
            thisMenu = LunchMenu()
            try:
                lunchFile.next() #skip header
                
                line = lunchFile.next()
                while line != None:
                    line = line.strip()
                    if cls.ignoreLine(line):
                        line = lunchFile.next()
                        continue
                    # we should be at the beginning of a day's lunch!!
                    
                    # line should contain date
                    try:
                        thisMenu.lunchDate = cls.checkDate(line.encode('utf-8'), messages)
                    except:
                        line = lunchFile.next()
                        continue
                                    
                    line = lunchFile.next().strip()
                    lastLineDesc = None
                    while not cls.isSeparatorLine(line):
                        if len(line) is 0:
                            line = lunchFile.next().strip()
                            continue
                        
                        #check if already new lunch menu, if no separator line
                        try:
                            cls.checkDate(line.encode('utf-8'), messages)
                            break
                        except:
                            # fine, is no new menu
                            pass
                        
                        # line should contain something to eat
                        lineDesc = None
                        lineContent = line
                        if ":" in line:
                            lineDesc = line[:line.find(":")].upper()
                            lineContent = line[line.find(":") + 1:].strip()
                        elif lastLineDesc != None and lastLineDesc == messages['mainDishesDisplayed']:
                            # check if they forgot the double dot after the or
                            if line.strip().upper().startswith(messages["mainDishesOrSource"]):
                                lineDesc = messages["mainDishesOrSource"]
                                lineContent = line.strip()[len(messages["mainDishesOrSource"]):].strip()
                        lastLineDesc = cls.handleLine(thisMenu, lineDesc, lineContent, lastLineDesc, messages)
                        line = lunchFile.next().strip()
                    cls.addMenu(thisMenu, lunchMenus)
                    thisMenu = LunchMenu()
            except StopIteration:
                # File read completely, add last menu
                cls.addMenu(thisMenu, lunchMenus)
        finally:
            lunchFile.close()
            
        return lunchMenus

LunchMenu.initialize()