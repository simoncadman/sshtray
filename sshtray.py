#! /usr/bin/env python2
#    SSHTray - SSH Systray menu
#    Copyright (C) 2013 Simon Cadman
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License    
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sip,sys,os,subprocess,time,getpass,ConfigParser,pickle
from functools import partial
sip.setapi('QVariant', 2)

from PyQt4 import QtGui
from PyQt4 import QtCore

import boto.ec2

# line below is replaced on commit
SSHTrayVersion = "20150604 215020"

class RefreshServers(QtCore.QThread):
    def __init__(self):
        self.refreshNow = False
        QtCore.QThread.__init__(self)
        self.connect(self, QtCore.SIGNAL('runNow'), self.refreshServersNow)

    def refreshServersNow(self):
        self.refreshNow = True

    def run(self):
        global window
        while True:
            if window.configLoaded == True:
                try:
                    window.refreshAction.setDisabled(True)
                    window.refreshAction.setText('Updating servers...')
                    data = self.refreshServers()
                    window.emit(QtCore.SIGNAL('updateMenu'), data)
                except Exception as e:
                    print "Error updating servers"
                    print e
            for i in range(1,window.configSleep):
                    if self.refreshNow  == True:
                           self.refreshNow = False
                           break
                    time.sleep(1)
        
    def refreshServers(self):
        global window
        print "Refreshing servers"
        accounts = {}
        for accountName in window.accountsList:
            print accountName, "updating"
            ec2instances = {}
            for region in [ 'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-1', 'sa-east-1', 'us-east-1' , 'us-west-1', 'us-west-2' ]:
                ec2_conn = boto.ec2.connect_to_region(region, aws_access_key_id=window.accountsList[accountName]['EC2AccessId'], aws_secret_access_key=window.accountsList[accountName]['EC2SecretKey'])
                for reservation in ec2_conn.get_all_instances():
                    for instance in reservation.instances:
                        instanceplatform = ""
                        if instance.platform != None:
                            instanceplatform = instance.platform
                        instancename = "Unknown " + instanceplatform + " Instance " + instance.id
                        if 'Name' in instance.tags:
                            instancename = instance.tags['Name']
                        if instance.region.name not in ec2instances:
                            ec2instances[instance.region.name] = {}
                        groupName = 'Other'
                        if 'aws:autoscaling:groupName' in instance.tags:
                            groupName = instance.tags['aws:autoscaling:groupName']
                        if window.configEC2TrayGroupName in instance.tags:
                            groupName = instance.tags[window.configEC2TrayGroupName]
                        if groupName not in ec2instances[instance.region.name]:
                            ec2instances[instance.region.name][groupName] = {}
                        ec2instances[instance.region.name][groupName][instance.id] = {'Name': instancename, 'IP' : instance.ip_address, 'Region' : instance.region.name, 'Status' : instance.state }
            accounts[accountName] = { 'instances' : ec2instances }
            print accountName, "updated"
        print "Servers updated"
        return {'ec2' : accounts }

class SSHTray(QtGui.QDialog):
    
    # loads config file, returns menu items
    def loadSettingsFromConfig(self):
        self.configLoaded = False
        self.appName = "sshtray"
        self.configFile = os.path.expanduser('~/.' + self.appName)
        
        # default settings
        self.configPort = str(22)
        self.configUsername = getpass.getuser()
        self.configSleep = 300
        self.configEC2TrayGroupName = 'TrayGroupName'
        self.accountsList = {}
        
        # load from file
        if os.path.exists(self.configFile):
            try:
                config = ConfigParser.ConfigParser()
                config.readfp(open(self.configFile))
                
                if config.has_section('ec2'):
                        self.accountsList = { 'Default' : { 'EC2AccessId' : config.get('ec2', 'accessid'), 'EC2SecretKey' : config.get('ec2', 'secretkey') } }
                        
                if config.has_section('ec2_accounts'):
                        self.accountsList = pickle.loads(config.get('ec2_accounts', 'details'))
                        
                if config.has_section('global'):
                        self.configUsername = config.get('global', 'username')
                        if config.has_option('global', 'PreRunScript'):
                            self.preRunScript = config.get('global', 'PreRunScript')
                        
                self.configLoaded = True
            except:
                pass
        
        return []
    
    def saveSettings(self):
        self.configLoaded = True
        self.configUsername = str(self.usernameEdit.text()).strip()
        self.preRunScript = str(self.runScriptEdit.text()).strip()
        config = ConfigParser.ConfigParser()
        config.add_section('global')
        config.set('global', 'username', self.configUsername )
        config.set('global', 'PreRunScript', self.preRunScript )
        
        config.add_section('ec2_accounts')
        self.accountsList = {}
        for tab in range(0,len(self.ec2AccountTabWidget)):
            tabWidget = self.ec2AccountTabWidget.widget(tab)
            layout = tabWidget.layout()
            accountName = ''
            EC2AccessId = ''
            EC2SecretKey = ''
            for widgetItem in range(0,len(layout)):
                widget = layout.itemAt(widgetItem)
                actualWidget = widget.widget()
                
                if actualWidget.__class__.__name__ == 'QLineEdit':
                    if actualWidget.objectName() == "AccountName":
                        accountName = str(actualWidget.text()).strip()
                        
                    if actualWidget.objectName() == "EC2AccessId":
                        EC2AccessId = str(actualWidget.text()).strip()
                        
                    if actualWidget.objectName() == "EC2SecretKey":
                        EC2SecretKey = str(actualWidget.text()).strip()
                    
            self.accountsList[accountName] = { 'EC2AccessId' : EC2AccessId, 'EC2SecretKey' : EC2SecretKey }
        config.set('ec2_accounts', 'details', pickle.dumps(self.accountsList) )
        config.write(open(self.configFile,'w'))
        self.refreshNow()

    def refreshNow(self):
        self.refreshAction.setDisabled(True)
        self.refreshAction.setText('Updating servers...')
        global refresh
        refresh.emit(QtCore.SIGNAL('runNow') )
        
    def resetSettings(self):
        self.usernameEdit.setText(self.configUsername)
        self.runScriptEdit.setText(self.preRunScript)
        
        # delete any existing tabs
        for tab in range(0,len(self.ec2AccountTabWidget)):
            self.ec2AccountTabWidget.removeTab(0)
        
        # actually allow users with no accounts to add initial account
        if len(self.accountsList) == 0:
            self.accountsList = { 'Default' : { 'EC2AccessId' : '', 'EC2SecretKey' : '' } }
        
        for accountName in self.accountsList:
            self.addEC2AccountTab(accountName , self.accountsList[accountName])
        
        # default to first tab
        self.ec2AccountTabWidget.setCurrentIndex(0)
    
    def __init__(self):
        self.trayIcon = None
        self.trayIconMenu = None
        self.ec2Menu = None
        self.preRunScript = ""
        
        super(SSHTray, self).__init__()
        
        # load settings from config
        data = self.loadSettingsFromConfig()
        
        # setup about menu
        self.aboutWindow = QtGui.QDialog()
        
        # setup the settings window
        self.setupSettings()

        # setup tray and menu on the tray
        self.setupMenuOptions({})
        self.setupTrayIcon()
        
        # connect refresh of menu options to signal
        self.connect(self, QtCore.SIGNAL('updateMenu'), self.setupMenuOptions)
        
        # all setup, show the tray icon
        self.trayIcon.show()
        
        if not self.configLoaded:
            self.showNormal()

    # user clicked tray, show menu
    def iconActivated(self, reason):
        if reason in (QtGui.QSystemTrayIcon.Trigger, QtGui.QSystemTrayIcon.DoubleClick):
            self.trayIconMenu.popup(QtGui.QCursor.pos())

    def saveSettingsButton(self):
        self.hide()
        self.saveSettings()

    def cancelSettingsButton(self):
        self.hide()
        self.resetSettings()

    def addEC2AccountTabButton ( self ):
        self.addEC2AccountTab('New', { 'EC2AccessId' : '', 'EC2SecretKey' : '' } )

    def removeEC2AccountTabButton ( self ):
        if self.ec2AccountTabWidget.count() > 1:
            selectedIndex = self.ec2AccountTabWidget.currentIndex()
            self.ec2AccountTabWidget.removeTab(selectedIndex)
    
    def updateEC2AccountTabName( self, text ):
        selectedIndex = self.ec2AccountTabWidget.currentIndex()
        self.ec2AccountTabWidget.setTabText(selectedIndex,text)
    
    def addEC2AccountTab ( self, accountName, details ):
        accountNameLabel = QtGui.QLabel("Account Name:")
        accountNameEdit = QtGui.QLineEdit()
        accountNameEdit.setText(accountName)
        accountNameEdit.setObjectName('AccountName')
        accountNameEdit.textChanged.connect(self.updateEC2AccountTabName)
        
        accountLabel = QtGui.QLabel("Access Key ID:")
        accountEdit = QtGui.QLineEdit()
        accountEdit.setObjectName('EC2AccessId')
        accountEdit.setText(details['EC2AccessId'])

        secretLabel = QtGui.QLabel("Secret Access Key:")
        secretEdit = QtGui.QLineEdit()
        secretEdit.setObjectName('EC2SecretKey')
        secretEdit.setText(details['EC2SecretKey'])
        secretEdit.setMinimumWidth(350)
        
        self.ec2AccountWidget = QtGui.QWidget()
        ec2Layout = QtGui.QGridLayout()
        
        ec2Layout.addWidget(accountNameLabel, 0, 0)
        ec2Layout.addWidget(accountNameEdit, 0, 1)
        
        ec2Layout.addWidget(accountLabel, 1, 0)
        ec2Layout.addWidget(accountEdit, 1, 1)
        
        ec2Layout.addWidget(secretLabel, 2, 0)
        ec2Layout.addWidget(secretEdit, 2, 1)
        
        self.ec2AccountWidget.setLayout(ec2Layout)
        newTabIndex = self.ec2AccountTabWidget.addTab(self.ec2AccountWidget, accountName)
        self.ec2AccountTabWidget.setCurrentIndex(newTabIndex)

    # settings window
    def setupSettings(self):
        
        self.globalSettingsGroupBox = QtGui.QGroupBox("Global Settings")
        self.globalSettingsLayout = QtGui.QGridLayout()
        self.globalGroupBox = QtGui.QGridLayout()

        usernameLabel = QtGui.QLabel("Default SSH Username:")
        self.usernameEdit = QtGui.QLineEdit()
        self.globalGroupBox.addWidget(usernameLabel, 0, 0)
        self.globalGroupBox.addWidget(self.usernameEdit, 0, 1)
        self.globalSettingsGroupBox.setLayout(self.globalGroupBox)
        
        runScriptLabel = QtGui.QLabel("Run Script Before Connecting:")
        self.runScriptEdit = QtGui.QLineEdit()
        self.globalGroupBox.addWidget(runScriptLabel, 1, 0)
        self.globalGroupBox.addWidget(self.runScriptEdit, 1, 1)
        self.globalSettingsGroupBox.setLayout(self.globalGroupBox)
        
        self.messageGroupBox = QtGui.QGroupBox("Amazon EC2")
        self.ec2AccountTabWidget = QtGui.QTabWidget()
        addEC2TabButton = QtGui.QPushButton("+")
        addEC2TabButton.clicked.connect(self.addEC2AccountTabButton)
        self.ec2AccountTabWidget.setCornerWidget(addEC2TabButton, QtCore.Qt.TopLeftCorner)
        
        removeTabButton = QtGui.QPushButton("-")
        removeTabButton.clicked.connect(self.removeEC2AccountTabButton)
        self.ec2AccountTabWidget.setCornerWidget(removeTabButton, QtCore.Qt.TopRightCorner)
        
        # save and cancel buttons
        footerGroupBox = QtGui.QGroupBox()
        footerLayout = QtGui.QHBoxLayout()
        footerGroupBox.setLayout(footerLayout)
        
        self.saveButton = QtGui.QPushButton("&Save")
        self.saveButton.setDefault(True)
        self.saveButton.clicked.connect(self.saveSettingsButton)
        
        self.cancelButton = QtGui.QPushButton("&Cancel")
        self.cancelButton.clicked.connect(self.cancelSettingsButton)
        
        footerLayout.addWidget(self.saveButton)
        footerLayout.addWidget(self.cancelButton)
        
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.globalSettingsGroupBox)
        mainLayout.addWidget(self.ec2AccountTabWidget)
        mainLayout.addWidget(footerGroupBox)
        self.setLayout(mainLayout)
        
        self.resetSettings()

    def doSSH(self, instance):
        print "SSHing",instance
        result = 0
        command = "konsole"
        if self.preRunScript != None and self.preRunScript != "":
            p2 = subprocess.Popen([self.preRunScript, instance])
            p2.wait()
        if os.environ.get('KDE_FULL_SESSION') == 'true':
                p = subprocess.Popen([command, '--new-tab','-e', 'ssh', '-p' + self.configPort, "-v", self.configUsername + '@' + instance], stdout=subprocess.PIPE)
        elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
                command=  'gnome-terminal'
                p = subprocess.Popen([command,'--tab', '-x', 'ssh', '-p' + self.configPort, "-v", self.configUsername + '@' + instance], stdout=subprocess.PIPE)
        result = p.returncode
        
    def showAbout(self):
        self.aboutWindow.showNormal()

    # options within tray context menu
    def setupMenuOptions(self, data):
        if self.trayIconMenu == None:
                # setup first time round menu
                self.trayIconMenu = QtGui.QMenu(self)
        
                # default data
                self.aboutAction = QtGui.QAction("&About SSHTray", self,
                        triggered=self.showAbout)
                self.settingsAction = QtGui.QAction("&Settings", self,
                        triggered=self.showNormal)
                self.refreshAction = QtGui.QAction("&Refresh Now", self,
                        triggered=self.refreshNow)
                self.quitAction = QtGui.QAction("&Quit", self,
                        triggered=QtGui.qApp.quit)
        
                # default, need to appear at end of list
                if self.trayIcon == None:
                        self.firstSeperator = self.trayIconMenu.addSeparator()
                        self.trayIconMenu.addAction(self.refreshAction)
                        self.refreshAction.setDisabled(True)
                        self.refreshAction.setText('Updating servers...')
                        self.trayIconMenu.addSeparator()
                        self.trayIconMenu.addAction(self.settingsAction)
                        self.trayIconMenu.addAction(self.aboutAction)
                        self.trayIconMenu.addAction(self.quitAction)
                        
        # ec2 instances
        if 'ec2' in data and len(data['ec2']) > 0:
            oldec2MenuAction = None
            if self.ec2Menu != None:
                    self.trayIconMenu.removeAction(self.ec2Menu.menuAction())
                    self.ec2Menu.clear()
                    sip.delete(self.ec2Menu)
            self.ec2Menu = QtGui.QMenu("&EC2", self)
            orderedAccounts = []
            orderedAccounts = sorted(data['ec2'])
            
            for orderedAccount in orderedAccounts:
                accountMenu = QtGui.QMenu(orderedAccount, self.ec2Menu)
                
                orderedRegions = []
                # sort regions
                orderedRegions = sorted(data['ec2'][orderedAccount]['instances'])
                for region in orderedRegions:
                    serverRegion = QtGui.QMenu(region,self.ec2Menu)
                    orderedGroups = sorted(data['ec2'][orderedAccount]['instances'][region])
                    for group in orderedGroups:
                        serverGroup = QtGui.QMenu(group,self.ec2Menu)
                        orderedInstances = sorted(data['ec2'][orderedAccount]['instances'][region][group],key=lambda instanceItem: str.lower(str(data['ec2'][orderedAccount]['instances'][region][group][instanceItem]['Name'])))
                        for instanceName in orderedInstances:
                            instance = data['ec2'][orderedAccount]['instances'][region][group][instanceName]
                            serverAction = QtGui.QAction(instance['Name'],self.ec2Menu)
                            if instance['Status'] != 'running':
                                    serverAction.setDisabled(True)
                            self.connect(serverAction,QtCore.SIGNAL("triggered()"), partial(self.doSSH, instance['IP']))
                            if len(data['ec2'][orderedAccount]['instances'][region]) > 1:
                                serverGroup.addAction(serverAction)
                            else:
                                if len(data['ec2'][orderedAccount]['instances']) > 1:
                                    serverRegion.addAction(serverAction)
                                else:
                                    if len(data['ec2']) > 1:
                                        self.ec2Menu.addMenu(accountMenu)
                                        accountMenu.addAction(serverAction)
                                    else:
                                        self.ec2Menu.addAction(serverAction)
                                        
                        if len(data['ec2'][orderedAccount]['instances'][region]) > 1:
                            if len(data['ec2'][orderedAccount]['instances']) > 1:
                                serverRegion.addMenu(serverGroup)
                            else:
                                if len(data['ec2']) > 1:
                                    accountMenu.addMenu(serverGroup)
                                else:
                                    self.ec2Menu.addMenu(serverGroup)
                    
                    if len(data['ec2']) > 1:
                        self.ec2Menu.addMenu(accountMenu)
                        if len(data['ec2'][orderedAccount]['instances']) > 1:
                            accountMenu.addMenu(serverRegion)
                    else:
                        if len(data['ec2'][orderedAccount]['instances']) > 1:
                            self.ec2Menu.addMenu(serverRegion)
                        
                self.trayIconMenu.insertMenu( self.firstSeperator , self.ec2Menu)
            
            self.trayIconMenu.insertMenu( self.firstSeperator , self.ec2Menu)
        
        if 'zeroconf' in data and len(data['zeroconf']) > 0:
            self.discoveredMenu = QtGui.QMenu("&Discovered", self)
            self.trayIconMenu.addMenu(self.discoveredMenu)
        
        if 'custom' in data and len(data['custom']) > 0:
            self.customMenu = QtGui.QMenu("&Custom", self)
            self.trayIconMenu.addMenu(self.customMenu)

        self.refreshAction.setDisabled(False)
        self.refreshAction.setText('&Refresh Now')
        
    # tray icon
    def setupTrayIcon(self):
         icon = QtGui.QIcon('sshtray.svg')
         self.trayIcon = QtGui.QSystemTrayIcon(icon)
         self.setWindowIcon(icon)
         self.trayIcon.setContextMenu(self.trayIconMenu)
         self.trayIcon.activated.connect(self.iconActivated)

if __name__ == '__main__':
    QtGui.QApplication.setAttribute(QtCore.Qt.AA_X11InitThreads, True)
    app = QtGui.QApplication(sys.argv)
    
    if not QtGui.QSystemTrayIcon.isSystemTrayAvailable():
        QtGui.QMessageBox.critical(None, "SSHTray", "Failed to detect a system tray.")
        sys.exit(1)
        
    QtGui.QApplication.setQuitOnLastWindowClosed(False)
    
    global window
    window = SSHTray()
    global refresh
    refresh = RefreshServers()
    refresh.start()
    sys.exit(app.exec_())
