# -*- coding: utf-8 -*-
from eurest_lunch_menu import LunchMenus, LunchMenu
from lunchinator import get_server, get_db_connection, get_settings
from lunchinator.plugin import iface_general_plugin, db_for_plugin_iface

from threading import Timer
from functools import partial
from lunchinator.logging_mutex import loggingMutex
    
class lunch_statistics(iface_general_plugin):
    def __init__(self):
        super(lunch_statistics, self).__init__()
        self.options = [((u"url", u"Lunch Menu URL", self._urlChanged), "")]
        self.statisticsThread = None
        self._lock = loggingMutex(u"Eurest Lunch Menu Statistics", logging=get_settings().get_verbose())
        self.add_supported_dbms("SQLite Connection", _SQLCommandsSQLite)
        #self.add_supported_dbms("SAP HANA Connection", __SQLCommandsHANA)

    def reconnect_db(self, _, newConnection):
        iface_general_plugin.reconnect_db(self, _, newConnection)
        self._stopTimer()
        self._startTimer()
        
    def _formatTitleAndDescription(self, title, description, keyInfo):
        if title and description:
            result = "%s, %s" % (title, description)
        elif title:
            result = title
        else:
            result = description
        
        if keyInfo:
            return "%s: %s" % (keyInfo.title(), result)
        return result
    
    def _insertOrUpdate(self, aLunchMenu, aLunchEntry, tableName):
        statDB = self.specialized_db_conn()
        if statDB is None:
            self.logger.warning("No database connection available, cannot update lunch statistics.")
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
            for title, description, additives, keyInfo in aLunchEntry:
                textAndAdditivesList.append((self._formatTitleAndDescription(title, description, keyInfo), ", ".join(additives)))
            statDB.insertLunchPart(aLunchMenu.lunchDate, textAndAdditivesList, doUpdate, tableName)
        return not upToDate
            
    def _updateLunchStatistics(self, url):
        with self._lock:
            self.lunchMenus.initialize(url)
            statDB = self.specialized_db_conn()
            
            if statDB is not None:
                englishLunchMenus = self.lunchMenus.getEnglishMenus()
                englishMessages = self.lunchMenus.getEnglishMessages()
                needCommit = False
                for aLunchMenu in englishLunchMenus:
                    if type(aLunchMenu) is LunchMenu:
                        if englishMessages['soupDisplayed'] in aLunchMenu.contents:
                            if self._insertOrUpdate(aLunchMenu,
                                                    aLunchMenu.contents[englishMessages['soupDisplayed']],
                                                    "LUNCH_SOUP"):
                                needCommit = True
                        if englishMessages['mainDishesDisplayed'] in aLunchMenu.contents:
                            if self._insertOrUpdate(aLunchMenu,
                                                    aLunchMenu.contents[englishMessages['mainDishesDisplayed']],
                                                    "LUNCH_MAIN"):
                                needCommit = True
                        if englishMessages['supplementsDisplayed'] in aLunchMenu.contents:
                            if self._insertOrUpdate(aLunchMenu,
                                                    aLunchMenu.contents[englishMessages['supplementsDisplayed']],
                                                    "LUNCH_SIDE"):
                                needCommit = True
                        if englishMessages['dessertsDisplayed'] in aLunchMenu.contents:
                            if self._insertOrUpdate(aLunchMenu,
                                                    aLunchMenu.contents[englishMessages['dessertsDisplayed']],
                                                    "LUNCH_DESSERT"):
                                needCommit = True
                            
                if needCommit:
                    statDB.get_db_conn().commit()
            self._startTimer(60*60)
            
    def _stopTimer(self, join=True):
        if self.timer is not None:
            self.timer.cancel()
            if join:
                self.timer.join()
            self.timer = None
            
    def _startTimer(self, timeout=0):
        if not self.get_option(u"url"):
            self.logger.warning("Cannot start lunch statistics thread, no URL given.")
        else:
            self.timer = Timer(timeout, partial(self._updateLunchStatistics, self.get_option(u"url")))
            self.timer.start()
    
    def _urlChanged(self, _setting, _newVal):
        self._stopTimer()
        self._startTimer()
    
    def activate(self):
        iface_general_plugin.activate(self)
        self.lunchMenus = LunchMenus(self.logger)
        self._startTimer()
            
    def deactivate(self):
        with self._lock:
            self._stopTimer(join=False)
        iface_general_plugin.deactivate(self)
        
    def get_displayed_name(self):
        return "Eurest Lunch Statistics"

class _SQLCommandsSQLite(db_for_plugin_iface):
    VERSION_INITIAL = 0
    VERSION_CURRENT = VERSION_INITIAL
    
    version_schema =       "CREATE TABLE LUNCH_STATISTICS_VERSION (VERSION INTEGER)"
    lunch_soup_schema =    "CREATE TABLE LUNCH_SOUP    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_main_schema =    "CREATE TABLE LUNCH_MAIN    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_side_schema =    "CREATE TABLE LUNCH_SIDE    (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)" 
    lunch_dessert_schema = "CREATE TABLE LUNCH_DESSERT (DATE DATE, NAME TEXT, ADDITIVES TEXT, LAST_UPDATE DATE)"
    
    def init_db(self):
        conn = self.get_db_conn()
        if not conn.existsTable("LUNCH_STATISTICS_VERSION"):
            conn.execute(self.version_schema)
            conn.execute("INSERT INTO LUNCH_STATISTICS_VERSION VALUES (?)", self.VERSION_CURRENT)
        if not conn.existsTable("LUNCH_SOUP"):
            conn.execute(self.lunch_soup_schema)
        if not conn.existsTable("LUNCH_MAIN"):
            conn.execute(self.lunch_main_schema)
        if not conn.existsTable("LUNCH_SIDE"):
            conn.execute(self.lunch_side_schema)
        if not conn.existsTable("LUNCH_DESSERT"):
            conn.execute(self.lunch_dessert_schema)
    
    def lastUpdateForLunchDay(self, date, tableName):
        conn = self.get_db_conn()
        sql="SELECT LAST_UPDATE FROM %s WHERE DATE=%s" % (conn.get_table_name(tableName),
                                                          conn.get_formatted_date(date))
        tuples = conn.query(sql)
        if tuples == None or len(tuples) == 0:
            self.logger.debug("%s -> None", sql)
            return None
        else:
            self.logger.debug("%s -> %s", sql, tuples)
            return conn.parse_result_date(tuples[0][0])
        
    def insertLunchPart(self, date, textAndAdditivesList, update, table):
        conn = self.get_db_conn()
        if update:
            sql="DELETE FROM %s WHERE DATE=%s" % (conn.get_table_name(table),
                                                  conn.get_formatted_date(date))
            conn.executeNoCommit(sql)
        for textAndAdditives in textAndAdditivesList:
            sql="INSERT INTO %s VALUES(%s, ?, ?, %s)" % (conn.get_table_name(table),
                                                         conn.get_formatted_date(date),
                                                         conn.get_formatted_date(date.today()))
            self.logger.debug("%s, %s, %s", sql, textAndAdditives[0], textAndAdditives[1])
            conn.executeNoCommit(sql, textAndAdditives[0], textAndAdditives[1])
        
class _SQLCommandsHANA(db_for_plugin_iface):
    def init_db(self):
        pass