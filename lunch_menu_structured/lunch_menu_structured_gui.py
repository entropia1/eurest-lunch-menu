# -*- coding: utf-8 -*-
import os
import inspect
import sys
import locale
import subprocess
from PyQt4.QtGui import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QComboBox, QTextEdit, QStackedWidget, QToolButton, QFont, QMessageBox, QSizePolicy, QTextListFormat
from PyQt4.QtCore import Qt, QObject, QSize, QEvent, QPoint

try:
    from lunchinator import log_exception, log_debug, convert_string
except ImportError:
    sys.path.insert(0, os.getenv("HOME") + "/.lunchinator-dist-sap")
    from lunchinator import log_exception, log_debug, convert_string

try:
    from lunch_menu import LunchMenu
except ImportError:
    currentFolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(os.path.split(inspect.getfile( inspect.currentframe() ))[0])[0])))
    if currentFolder not in sys.path:
        sys.path.insert(0, currentFolder)
    from lunch_menu import LunchMenu
    
class GrowingTextEdit(QTextEdit):
    def __init__(self, parent, messages):
        super(GrowingTextEdit, self).__init__(parent)  
        self.document().contentsChanged.connect(self.sizeChange)

        self.additives = {}
        self.messages = messages
        self.heightMin = 0
        self.heightMax = 65000
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
        self.sizeChange()

    def resizeEvent(self, *args, **kwargs):
        self.sizeChange()
        return QTextEdit.resizeEvent(self, *args, **kwargs)

    def sizeChange(self):
        docHeight = self.document().size().height()
        if self.heightMin <= docHeight <= self.heightMax:
            self.setMinimumHeight(docHeight)
            self.setMaximumHeight(docHeight)
            
    def setVisible(self, *args, **kwargs):
        QTextEdit.setVisible(self, *args, **kwargs)
        self.sizeChange()
            
    def sizeHint(self):
        return QSize(QWidget.sizeHint(self).width(), self.minimumHeight())
    
    def showToolTip(self, posX, posY):
        cursor = self.cursorForPosition(QPoint(posX, posY))
        offset = cursor.position()
        if offset in self.additives:
            self.setToolTip(u"%s: %s" % (self.additives[offset], self.messages[u"additive_%s" % self.additives[offset]]))
    
    def event(self, event):
        if event.type() == QEvent.ToolTip:
            self.showToolTip(event.x(), event.y())
        return QTextEdit.event(self, event)
            
class lunch_menu_structured_gui(QWidget):
    textViewIndex = 0
    textViewAdditivesMap = {}
    
    def __init__(self, parent):
        super(lunch_menu_structured_gui, self).__init__(parent)
        
        self.messages = LunchMenu.messages()
        self.toggleMessages = LunchMenu.toggleMessages()
        
        layout = QVBoxLayout(self)
        
        buttonBar = self.createButtonBar(self)
        
        layout.addLayout(buttonBar)
        
        self.menuNotebook = QStackedWidget(self)
        self.createNotebook()
        layout.addWidget(self.menuNotebook)
        
        self.goToday()
        
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)
    
    def create_arrow_button(self, parent, arrow_type):
        button = QToolButton(parent)
        button.setArrowType(arrow_type)
        return button
    
    def goLeft(self):
        curIndex = self.combobox.currentIndex()
        if curIndex > 0:
            self.combobox.setCurrentIndex(curIndex - 1)
    
    def goRight(self):
        curIndex = self.combobox.currentIndex()
        if curIndex < 4:
            self.combobox.setCurrentIndex(curIndex + 1)
    
    def goToday(self):
        now = LunchMenu.today()
        
        minDelta = sys.maxint
        minDeltaI = 0
        i = 0
        for aLunchMenu in LunchMenu.allLunchMenus():
            if aLunchMenu == None or isinstance(aLunchMenu, Exception):
                # parse error, use current day of week
                if now.weekday() < 5:
                    minDeltaI = now.weekday()
                else:
                    minDeltaI = 4
                break
            td = now - aLunchMenu.lunchDate
            delta = abs((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6)
            if delta < minDelta:
                minDelta = delta
                minDeltaI = i
            i = i + 1
                
        self.combobox.setCurrentIndex(minDeltaI)
            
    def goTodayClicked(self):
        self.goToday()
        
    def isToggled(self):
        index = self.menuNotebook.currentIndex()
        return (index >= 5)
        
    def changed_combo(self,index):
        if self.isToggled():
            self.menuNotebook.setCurrentIndex(index + 5)
        else:
            self.menuNotebook.setCurrentIndex(index)
        self.leftButton.setEnabled(index != 0)
        self.rightButton.setEnabled(index != 4)
   
    def toggleLanguage(self):
        index = self.menuNotebook.currentIndex()
        isToggle = (index >= 5)
        if isToggle:
            self.switchLanguageButton.setText(self.messages["toggleLanguage"])
            index = index - 5
        else:
            self.switchLanguageButton.setText(self.messages["toggleLanguage2"])
            index = index + 5
        self.menuNotebook.setCurrentIndex(index)
   
    def createButtonBar(self, parent):
        self.combobox = QComboBox(parent)
        self.combobox.addItem(self.messages['monday'])
        self.combobox.addItem(self.messages['tuesday'])
        self.combobox.addItem(self.messages['wednesday'])
        self.combobox.addItem(self.messages['thursday'])
        self.combobox.addItem(self.messages['friday'])
        self.combobox.currentIndexChanged.connect(self.changed_combo)
        comboBoxHeight = self.combobox.sizeHint().height()
        
        self.leftButton = self.create_arrow_button(parent, Qt.LeftArrow)
        self.leftButton.clicked.connect(self.goLeft)
        self.leftButton.setMinimumSize(comboBoxHeight, comboBoxHeight)
        
        self.rightButton = self.create_arrow_button(parent, Qt.RightArrow)
        self.rightButton.clicked.connect(self.goRight)
        self.rightButton.setMinimumSize(comboBoxHeight, comboBoxHeight)
        
        
        navButtons = QHBoxLayout()
        navButtons.addWidget(self.leftButton, 0, Qt.AlignRight)
        navButtons.addWidget(self.combobox, 0, Qt.AlignCenter)
        navButtons.addWidget(self.rightButton, 0, Qt.AlignLeft)
        
        buttonBar = QHBoxLayout()
        todayButton = QPushButton(self.messages['today'], parent)
        todayButton.clicked.connect(self.goTodayClicked)
        todayButton.setMinimumHeight(comboBoxHeight)
        buttonBar.addWidget(todayButton)
        
        buttonBar.addWidget(QWidget(parent), 1)
        buttonBar.addLayout(navButtons, 1)
        buttonBar.addWidget(QWidget(parent), 1)
        
        self.switchLanguageButton = QPushButton(self.messages["toggleLanguage"], parent)
        self.switchLanguageButton.clicked.connect(self.toggleLanguage)
        self.switchLanguageButton.setMinimumHeight(comboBoxHeight)
        buttonBar.addWidget(self.switchLanguageButton, 0, Qt.AlignRight)
                
        return buttonBar
    
    def addMenuLine(self, parent, text, box, header = False):
        aLabel = QLabel(text, parent)
        if header:
            aLabel.setAlignment(Qt.AlignCenter)
            oldFont = aLabel.font()
            aLabel.setFont(QFont(oldFont.family(), 13, QFont.Bold))
        box.addWidget(aLabel)
        
    def addLocaleErrorPage(self, parent, box, toggle):
        aLabel = QLabel(self.messages['parseLocaleError'], parent)
        aLabel.setWordWrap(True)
        box.addWidget(aLabel)
        
        aButton = QPushButton(self.messages['installLocaleButton'], parent)
        if toggle:
            aButton.clicked.connect(self.installLanguageSupportToggle)
        else:
            aButton.clicked.connect(self.installLanguageSupport)
        box.addWidget(aButton)
        
    def addExceptionPage(self, parent, box, error, toggle):
        aLabel = QLabel(self.messages['otherException'] + u" " + unicode(error), parent)
        aLabel.setWordWrap(True)
        box.addWidget(aLabel)
        
    def installLanguageSupportForLocale(self, locale):
        locale = locale.partition("_")[0]
        if subprocess.call(['gksu', "apt-get -q -y install language-pack-%s" % locale])!=0:
            QMessageBox().critical(self.menuNotebook, "Installation Error", self.messages['installLocaleError'], buttons=QMessageBox.Ok, defaultButton=QMessageBox.Ok)
        else:
            QMessageBox().information(self.menuNotebook, "Success", self.messages['installLocaleSuccess'], buttons=QMessageBox.Ok, defaultButton=QMessageBox.Ok)
    
    def installLanguageSupport(self):
        self.installLanguageSupportForLocale(self.defaultLocaleString)
    def installLanguageSupportToggle(self):
        self.installLanguageSupportForLocale(self.messages['toggleLocale'])

    def addMenuContent(self, parent, desc, menuContents, box, messages):
        self.addMenuLine(parent, desc, box)
        if desc in menuContents:
            content = menuContents[desc]
        else:
            content = messages[u'noContents']
            log_debug("lunch menu does not contain key '%s'" % desc)
        
        textview = GrowingTextEdit(parent, self.messages)
        textview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        textview.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        textview.setLineWrapMode(QTextEdit.WidgetWidth)
        textview.setReadOnly(True)
        textview.document().setIndentWidth(10)
        
        if type(content) in (unicode, str):
            textview.append(content)
        elif type(content) is list:
            cursor = textview.textCursor()
            listFormat = QTextListFormat()
            listFormat.setStyle(QTextListFormat.ListDisc)
            listFormat.setIndent(1)
            cursor.createList(listFormat)
            for content_line in content:
                textview.append(content_line)
        
        additives = LunchMenu.findAdditives(convert_string(textview.toPlainText()))
        textview.additives = additives
        
        box.addWidget(textview, 0)
    
    def createNotebook(self):
        for _ in range(self.menuNotebook.count()):
            self.menuNotebook.remove(self.menuNotebook.widget(0))
        curMessages = self.messages
        for index in range(10):
            if index == 5:
                try:
                    locale.setlocale(locale.LC_TIME, (self.messages["toggleLocale"],"UTF-8"))
                except:
                    log_exception("error setting locale")
                curMessages = self.toggleMessages
            pageWidget = QWidget(self.menuNotebook)
            page = QVBoxLayout(pageWidget)
            thisLunchMenu = LunchMenu.allLunchMenus()[index]
            if thisLunchMenu != None and type(thisLunchMenu) == LunchMenu:
                title = curMessages['lunchMenuFor'] + u" " + thisLunchMenu.lunchDate.strftime(curMessages['dateFormatDisplayed']).decode("utf-8")
                self.addMenuLine(pageWidget, title, page, True)
                if thisLunchMenu.isValid():
                    self.addMenuContent(pageWidget, curMessages['soupDisplayed'], thisLunchMenu.contents, page, curMessages)
                    self.addMenuContent(pageWidget, curMessages['mainDishesDisplayed'], thisLunchMenu.contents, page, curMessages)
                    self.addMenuContent(pageWidget, curMessages['supplementsDisplayed'], thisLunchMenu.contents, page, curMessages)
                    self.addMenuContent(pageWidget, curMessages['dessertsDisplayed'], thisLunchMenu.contents, page, curMessages)
                else:
                    self.addMenuLine(pageWidget, curMessages['noLunchToday'], page)
            elif type(thisLunchMenu) == locale.Error:
                self.addLocaleErrorPage(pageWidget, page, index >= 5)
                pass
            elif isinstance(thisLunchMenu, Exception):
                self.addExceptionPage(pageWidget, page, thisLunchMenu, index >= 5)
            
            self.menuNotebook.addWidget(pageWidget)
        try:
            locale.setlocale(locale.LC_TIME, (LunchMenu.defaultLocaleString,"UTF-8"))
        except:
            log_exception("error setting locale")


if __name__ == "__main__":
    from lunchinator.iface_plugins import iface_gui_plugin
    iface_gui_plugin.run_standalone(lambda window: lunch_menu_structured_gui(window))
