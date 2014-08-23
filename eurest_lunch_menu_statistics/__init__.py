# -*- coding: utf-8 -*-
import threading
import os
import inspect
import sys
import time
from eurest_lunch_menu import LunchMenus, LunchMenu
from lunchinator import get_server, get_db_connection
from lunchinator.plugin import iface_general_plugin

class LunchStatisticsThread(threading.Thread):
    def __init__(self, url, logger):
        threading.Thread.__init__(self)
        self.lunchMenus = LunchMenus(logger)
        self._url = url
        self.logger = logger
        self.stopped = False
        self.statDBErrorLogged = False
    
    def statsDB(self):
        stats, _type = get_db_connection(self.logger)
        if stats == None and not self.statDBErrorLogged:
            self.statDBErrorLogged = True
            self.logger.error("Lunch Statistics Plugin: No database connection available.")
        return stats
    
    def insertOrUpdate(self, aLunchMenu, aLunchEntry, tableName):
        statDB = self.statsDB()
        if not statDB:
            return
        lastUpdate = statDB.lastUpdateForLunchDay(aLunchMenu.lunchDate, tableName)
        upToDate=True
        doUpdate=False
        
        if lastUpdate == None:
            upToDate = False
        elif lastUpdate < self.lunchMenus.today():
            upToDate = False
            doUpdate = True
            
        if not upToDate:
            textAndAdditivesList = []
            if type(aLunchEntry) == list:
                for anEntry in aLunchEntry:
                    textAndAdditivesList.append(self.lunchMenus.extractAdditives(anEntry))
            else:
                textAndAdditivesList.append(self.lunchMenus.extractAdditives(aLunchEntry))
            statDB.insertLunchPart(aLunchMenu.lunchDate, textAndAdditivesList, doUpdate, tableName)
    
    def run(self):
        while True:
            self.lunchMenus.initialize(self._url)
            statDB = self.statsDB()
            if self.stopped:
                if statDB:
                    statDB.close()
                break
            
            if statDB != None:
                englishLunchMenus = self.lunchMenus.getEnglishMenus()
                englishMessages = self.lunchMenus.getEnglishMessages()
                needCommit = False
                for aLunchMenu in englishLunchMenus:
                    if type(aLunchMenu) is LunchMenu:
                        needCommit = True
                        if englishMessages['soupDisplayed'] in aLunchMenu.contents:
                            self.insertOrUpdate(aLunchMenu, aLunchMenu.contents[englishMessages['soupDisplayed']], "LUNCH_SOUP")
                        if englishMessages['mainDishesDisplayed'] in aLunchMenu.contents:
                            self.insertOrUpdate(aLunchMenu, aLunchMenu.contents[englishMessages['mainDishesDisplayed']], "LUNCH_MAIN")
                        if englishMessages['supplementsDisplayed'] in aLunchMenu.contents:
                            self.insertOrUpdate(aLunchMenu, aLunchMenu.contents[englishMessages['supplementsDisplayed']], "LUNCH_SIDE")
                        if englishMessages['dessertsDisplayed'] in aLunchMenu.contents:
                            self.insertOrUpdate(aLunchMenu, aLunchMenu.contents[englishMessages['dessertsDisplayed']], "LUNCH_DESSERT")
                            
                if needCommit:
                    statDB.commit()
            
            time.sleep(60*60)
            
    def stop(self):
        self.stopped = True

class lunch_statistics(iface_general_plugin):
    def __init__(self):
        super(lunch_statistics, self).__init__()
        self.options = [((u"url", u"Lunch Menu URL", self._urlChanged), "")]
        self.statisticsThread = None
        
    def _startThread(self, url):
        if self.statisticsThread != None:
            self.statisticsThread.stop()
            self.statisticsThread = None
        if not url:
            self.logger.error("Cannot start lunch statistics thread, no URL given.")
        else:
            self.statisticsThread = LunchStatisticsThread(url, self.logger)
            self.statisticsThread.start()
    
    def _urlChanged(self, _setting, newVal):
        self._startThread(newVal)
        return newVal
    
    def activate(self):
        iface_general_plugin.activate(self)
        # TODO
        #url = self.get_option(u"url")
        #self._startThread(url)
            
    def deactivate(self):
        if self.statisticsThread != None:
            self.statisticsThread.stop()
            self.statisticsThread = None
        iface_general_plugin.deactivate(self)
        
    def get_displayed_name(self):
        return "Eurest Lunch Statistics"

