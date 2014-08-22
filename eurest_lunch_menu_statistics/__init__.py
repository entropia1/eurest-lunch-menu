# -*- coding: utf-8 -*-
import threading
import os
import inspect
import sys
import time
from eurest_lunch_menu import LunchMenu
from lunchinator import get_server
from lunchinator.plugin import iface_general_plugin
from lunchinator.log import getLogger

class LunchStatisticsThread(threading.Thread):
    def __init__(self, connectionPlugin):
        threading.Thread.__init__(self)
        self.stopped = False
        self.connectionPlugin = connectionPlugin
        self.statDBErrorLogged = False
    
    def statsDB(self):
        stats = get_server().getDBConnection()
        if stats == None and not self.statDBErrorLogged:
            self.statDBErrorLogged = True
            getLogger().error("Lunch Statistics Plugin: No database connection available.")
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
        elif lastUpdate < LunchMenu.today():
            upToDate = False
            doUpdate = True
            
        if not upToDate:
            textAndAdditivesList = []
            if type(aLunchEntry) == list:
                for anEntry in aLunchEntry:
                    textAndAdditivesList.append(LunchMenu.extractAdditives(anEntry))
            else:
                textAndAdditivesList.append(LunchMenu.extractAdditives(aLunchEntry))
            statDB.insertLunchPart(aLunchMenu.lunchDate, textAndAdditivesList, doUpdate, tableName)
    
    def run(self):
        while True:
            # wait until connection is open
            # TODO can I wait until database connection plugin is activated? Maybe activate first?
            time.sleep(10)
            statDB = self.statsDB()
            if self.stopped:
                if statDB:
                    statDB.close()
                break
            
            if statDB != None:
                englishLunchMenus = LunchMenu.getEnglishMenus()
                englishMessages = LunchMenu.getEnglishMessages()
                needCommit = False
                for aLunchMenu in englishLunchMenus:
                    if type(aLunchMenu) == LunchMenu:
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
        self.statisticsThread = None
        
    def activate(self):
        iface_general_plugin.activate(self)
        # TODO
        #pluginInfo = PluginManagerSingleton.get().getPluginByName("Database Connection", "general")
        #if not pluginInfo.plugin_object.is_activated:
            #log_error("Lunch Statistics Plugin: Database connection plugin not activated.")
            #return
        #self.statisticsThread = LunchStatisticsThread(pluginInfo)
        #self.statisticsThread.start()
            
    def deactivate(self):
        if self.statisticsThread != None:
            self.statisticsThread.stop()
        iface_general_plugin.deactivate(self)
        
    def get_displayed_name(self):
        return "Eurest Lunch Statistics"

