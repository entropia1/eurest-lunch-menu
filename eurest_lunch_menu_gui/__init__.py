# -*- coding: utf-8 -*-
from lunchinator.plugin import iface_gui_plugin
from eurest_lunch_menu_gui.lunch_menu_widget import LunchMenuWidget
from eurest_lunch_menu import LunchMenu
from lunchinator.cli import LunchCLIModule
from lunchinator.callables import AsyncCall
from functools import partial

class lunch_menu_structured(iface_gui_plugin, LunchCLIModule):
    def __init__(self):
        iface_gui_plugin.__init__(self)
        LunchCLIModule.__init__(self)
        self.options = [((u"url", u"Lunch Menu URL", self._urlChanged), "")]
        self._initLunchMenu = None
        
    def activate(self):
        iface_gui_plugin.activate(self)
        self._widget = None
        
    def deactivate(self):
        iface_gui_plugin.deactivate(self)
    
    def get_displayed_name(self):
        return "Eurest Lunch Menu"

    def create_widget(self, parent):
        self._widget = LunchMenuWidget(parent)
        # TODO update regularly
        self._initLunchMenu = AsyncCall(self._widget,
                                        self.logger,
                                        LunchMenu.initialize,
                                        self._widget.createNotebook)

        # first time, call initializeLayout instead of createNotebook        
        AsyncCall(self._widget,
                  self.logger,
                  LunchMenu.initialize,
                  self._widget.initializeLayout)(self.get_option(u"url"))
        return self._widget
    
    def destroy_widget(self):
        self._initLunchMenu = None
        self._widget = None
        iface_gui_plugin.destroy_widget(self)
    
    def _urlChanged(self, _oldVal, newVal):
        if self._widget != None:
            self._initLunchMenu(newVal)
        return newVal
    
    def add_menu(self,menu):
        pass
    
    def getWeekdays(self):
        return [day.lower() for day in LunchMenu.getEnglishWeekdays()]
    
    def handleCommand(self, cmd):
        cmd = cmd.lower()
        if cmd in self.getWeekdays():
            self.weekdayToPrint = self.getWeekdays().index(cmd)
            return True
        elif cmd == 'tomorrow':
            self.weekdayToPrint = self.weekdayToPrint + 1
            return True
        elif cmd == 'de':
            self.languageToPrint = 'de'
            return True
        elif cmd == 'en':
            self.languageToPrint = 'en'
            return True
        else:
            print "unknown command: %s" % cmd
            self.printHelp("lunchmenu")
            return False
    
    def do_lunchmenu(self, args):
        """
        Print the lunch menu.
        Usage: lunchmenu [de | en]                              - print today's lunch menu, in German or English
               lunchmenu today | tomorrow | <weekday> [de | en] - print lunch menu of a specific week day
        """
        import shlex
        args = shlex.split(args)
        
        self.weekdayToPrint = LunchMenu.today().weekday()
        self.languageToPrint = LunchMenu.defaultLocaleString
        
        if len(args) > 0:
            if not self.handleCommand(args.pop(0)):
                return False
            
        if len(args) > 0:
            if not self.handleCommand(args.pop(0)):
                return False
            
        lunchMenu = LunchMenu.getLunchMenu(self.weekdayToPrint, self.languageToPrint)
        if lunchMenu == None:
            print "No lunch for this day."
        else:
            print "*** Lunch menu for %s ***" % (lunchMenu.lunchDate.strftime(LunchMenu.getEnglishMessages()['dateFormatDisplayed']))
            
            messages = LunchMenu.getMessages(self.languageToPrint)
            print "%s: %s" % (messages['soupDisplayed'], lunchMenu.contents[messages['soupDisplayed']])
            print "%s:" % messages['supplementsDisplayed']
            for aSideDish in lunchMenu.contents[messages['supplementsDisplayed']]:
                print " - %s" % aSideDish
            print "%s:" % messages['mainDishesDisplayed']
            for aSideDish in lunchMenu.contents[messages['mainDishesDisplayed']]:
                print " - %s" % aSideDish
            print "%s:" % messages['dessertsDisplayed']
            for aSideDish in lunchMenu.contents[messages['dessertsDisplayed']]:
                print " - %s" % aSideDish
        
    def complete_lunchmenu(self, text, line, begidx, endidx):
        argNum, text = self.getArgNum(text, line, begidx, endidx)
        
        if argNum == 1:
            # subcommand
            allCommands = ["de", "en", "today", "tomorrow"] + self.getWeekdays()
            return [aVal for aVal in allCommands if aVal.startswith(text)]
        elif argNum == 2:
            return [aVal for aVal in ("de", "en") if aVal.startswith(text)]
        
