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
import sip,sys,os,subprocess,time,getpass,ConfigParser
from functools import partial
sip.setapi('QVariant', 2)

from PyQt4 import QtGui
from PyQt4 import QtCore

import boto.ec2

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
            if window.configEC2AccessId != "" and window.configEC2SecretKey != "":
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
        ec2instances = {}
        for region in [ 'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2', 'eu-west-1', 'sa-east-1', 'us-east-1' , 'us-west-1', 'us-west-2' ]:
            ec2_conn = boto.ec2.connect_to_region(region, aws_access_key_id=window.configEC2AccessId, aws_secret_access_key=window.configEC2SecretKey)
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
        print "Servers updated"
        return {'ec2' : ec2instances }

class SSHTray(QtGui.QDialog):
    
    # loads config file, returns menu items
    def loadSettingsFromConfig(self):
        self.appName = "sshtray"
        self.configFile = os.path.expanduser('~/.' + self.appName)
        
        # default settings
        self.configEC2AccessId = ""
        self.configEC2SecretKey = ""
        self.configPort = str(22)
        self.configUsername = getpass.getuser()
        self.configSleep = 300
        self.configEC2TrayGroupName = 'TrayGroupName'

        # load from file
        if os.path.exists(self.configFile):
            try:
                config = ConfigParser.ConfigParser()
                config.readfp(open(self.configFile))
                if config.has_section('ec2'):
                        self.configEC2AccessId = config.get('ec2', 'accessid')
                        self.configEC2SecretKey = config.get('ec2', 'secretkey')
                if config.has_section('global'):
                        self.configUsername = config.get('global', 'username')
            except:
                pass
            
        return []
    
    def saveSettings(self):
        self.configEC2AccessId = str(self.accountEdit.text())
        self.configEC2SecretKey = str(self.secretEdit.text())
        self.configUsername = str(self.usernameEdit.text())
        config = ConfigParser.ConfigParser()
        config.add_section('global')
        config.set('global', 'username', self.configUsername )

        config.add_section('ec2')
        config.set('ec2', 'accessid', self.configEC2AccessId )
        config.set('ec2', 'secretkey', self.configEC2SecretKey )
        config.write(open(self.configFile,'w'))
        self.refreshNow()

    def refreshNow(self):
        self.refreshAction.setDisabled(True)
        self.refreshAction.setText('Updating servers...')
        global refresh
        refresh.emit(QtCore.SIGNAL('runNow') )
        
    def resetSettings(self):
        self.accountEdit.setText(self.configEC2AccessId)
        self.secretEdit.setText(self.configEC2SecretKey)
        self.usernameEdit.setText(self.configUsername)
    
    def __init__(self):
        self.trayIcon = None
        self.trayIconMenu = None
        self.ec2Menu = None
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
        
        if self.configEC2AccessId == "" or self.configEC2SecretKey == "":
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
        
        self.messageGroupBox = QtGui.QGroupBox("Amazon EC2")

        accountLabel = QtGui.QLabel("Access Key ID:")
        self.accountEdit = QtGui.QLineEdit()

        secretLabel = QtGui.QLabel("Secret Access Key:")
        self.secretEdit = QtGui.QLineEdit()
        
        self.saveButton = QtGui.QPushButton("&Save")
        self.saveButton.setDefault(True)
        self.saveButton.clicked.connect(self.saveSettingsButton)
        
        self.cancelButton = QtGui.QPushButton("&Cancel")
        self.cancelButton.clicked.connect(self.cancelSettingsButton)

        ec2Layout = QtGui.QGridLayout()
        ec2Layout.addWidget(accountLabel, 0, 0)
        ec2Layout.addWidget(self.accountEdit, 0, 1)
        ec2Layout.addWidget(secretLabel, 1, 0)
        ec2Layout.addWidget(self.secretEdit, 1, 1)
        ec2Layout.addWidget(self.saveButton, 2, 0)
        ec2Layout.addWidget(self.cancelButton, 2, 1)
        self.messageGroupBox.setLayout(ec2Layout)
        
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addWidget(self.globalSettingsGroupBox)
        mainLayout.addWidget(self.messageGroupBox)
        self.setLayout(mainLayout)
        
        self.resetSettings()

    def doSSH(self, instance):
        print "SSHing",instance
        result = 0
        command = "konsole"
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
                    oldec2MenuAction = self.ec2Menu.menuAction()
            self.ec2Menu = QtGui.QMenu("&EC2", self)
            orderedRegions = []
            # sort regions
            orderedRegions = sorted(data['ec2'])
            for region in orderedRegions:
                serverRegion = QtGui.QMenu(region,self)
                orderedGroups = sorted(data['ec2'][region])
                for group in orderedGroups:
                    serverGroup = QtGui.QMenu(group,self)
                    orderedInstances = sorted(data['ec2'][region][group],key=lambda instanceItem: str.lower(str(data['ec2'][region][group][instanceItem]['Name'])))
                    for instanceName in orderedInstances:
                        instance = data['ec2'][region][group][instanceName]
                        serverAction = QtGui.QAction(instance['Name'],self)
                        if instance['Status'] != 'running':
                                serverAction.setDisabled(True)
                        self.connect(serverAction,QtCore.SIGNAL("triggered()"), partial(self.doSSH, instance['IP']))
                        if len(data['ec2'][region]) > 1:
                            serverGroup.addAction(serverAction)
                        else:
                            if len(data['ec2']) > 1:
                                serverRegion.addAction(serverAction)
                            else:
                                self.ec2Menu.addAction(serverAction)
                    if len(data['ec2'][region]) > 1:
                        if len(data['ec2']) > 1:
                            serverRegion.addMenu(serverGroup)
                        else:
                            self.ec2Menu.addMenu(serverGroup)
                        
                if len(data['ec2']) > 1:
                    self.ec2Menu.addMenu(serverRegion)
            
            # remove existing ec2 menu
            if oldec2MenuAction != None:
                self.trayIconMenu.removeAction(oldec2MenuAction)
            
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
