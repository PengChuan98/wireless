import subprocess
import os, sys, time
import traceback

class createExe(object):

    def checkrequirements(self):
        allrequired = True
        requiredpipmodules = ['numpy','PyQt4','configobj','visa','serial','win32com.client','argparse','paramiko','pandas','pysnmp']
        for mods in requiredpipmodules:
            try:
                globals()[mods] = __import__(mods)
            except ImportError:
                allrequired = False
                traceback.print_exc()
                pass
        requiredmodules = ['AccessPoint.pyc','AccessPointWl.py','AccessPointWl.pyc','e1200v2.pyc','ea6300.pyc',
'f9k1102v1.pyc','html_reader.pyc','netgear.pyc','r7000.pyc','rtn66u.pyc','sbg6580.pyc','tlwr841nv11.pyc','tlwr841v72.pyc',
'tplink.pyc','wnr2000v2.pyc','wnr3500v1.pyc','AntPattern.py','AP.py','autoNF.py','channel_change.py','compileCode.py',
'agilent_j7211a.py','apcpdu.py','commands.py','menu.py','snmp.py','atten.py','device.py','gpib_devices.py','device.py',
'jfw50pa.py','jfw50pa_base.py','jfw50pa_ethernet.py','jfw50pa_ether_config.py','jfw50pa_exceptions.py','jfw50pa_serial.py',
'device.py','rc4dat.py','rc4dat_base.py','rc4dat_ethernet.py','rc4dat_ether_config.py','rc4dat_exceptions.py','rc4dat_usb.py',
'repow.py','tilt.py','turntable.py','GUIWiFiTest.py','hpTCP.py','ota.py','TancCommon.py','threadwatcher.py','timing.py',
'WirelessTesting.py']
        currentfiles = []
        for root, dirs, files in os.walk(os.getcwd()):
            currentfiles.extend(files)
        for m in requiredmodules:
            if not (m in currentfiles):
                allrequired = False
                print m, ' is missing'
        try:
            subprocess.check_output(["python", "-m","pip","show","pyinstaller"])
        except subprocess.CalledProcessError:
            print 'pyinstaller is not installed'
            allrequired = False
            
        return allrequired
        
    def setmodulespaths(self):
        def getmodlocation(path, name):
            full = os.path.join(path,name)
            prefix = full.split('C:\\Python27\\Lib\\site-packages')[1]
            location = "'"+prefix.replace(os.sep,'.').lstrip('.')+"'"
            return location
            
        pathsexist = True
        if os.path.exists('C:\\Python27\\Lib\\site-packages\\pysnmp'):
            self.pysnmp_path = "'"+r'C:\\Python27\\Lib\\site-packages\\pysnmp'+"'"
        else:
            print 'pysnmp not installed'
            pathsexist = False
        if os.path.exists('C:\\Python27\\Lib\\site-packages\\pysmi'):
            self.pysmi_path = "'"+r'C:\\Python27\\Lib\\site-packages\\pysmi'+"'"
            if os.path.exists('C:\\Python27\\Lib\\site-packages\\pysnmp\\smi\\mibs'):
                self.mibs_path = "'"+r'C:\\Python27\\Lib\\site-packages\\pysnmp\\smi\\mibs'+"'"
            else:
                print 'pysmi\smi\mibs missing'
                pathsexist = False
        else:
            print 'pysmi not installed'
            pathsexist = False
        if os.path.exists('C:\\Python27\\Lib\\site-packages\\dateutil\\tz'):
            self.dateutil_path = "'"+r'C:\\Python27\\Lib\\site-packages\\dateutil\\tz'+"'"
        elif os.path.exists('C:\\Python27\\Lib\\site-packages\\dateutil'):
            self.dateutil_path = "'"+r'C:\\Python27\\Lib\\site-packages\\dateutil'+"'"
        else:
            print 'dateutils not installed'
            pathsexist = False
        try:            
            for root, dirs, files in os.walk('C:\\Python27\\Lib\\site-packages\\pysnmp'):
                if 'exval.py' in files:
                    self.exval = getmodlocation(root, "exval")
                if 'cache.py' in files and os.path.basename(root) == 'pysnmp':
                    self.cache = getmodlocation( root,  "cache")
                if 'mibs' in dirs:
                    self.mibs = getmodlocation( root, "mibs")
                if 'instances' in dirs:
                    self.instances = getmodlocation( root, "instances")      
            for root, dirs, files in os.walk('C:\\Python27\\Lib\\site-packages\\dateutil'):
                if 'tz.py' in files:
                    self.tz = getmodlocation( root, 'tz')
        except Exception:
            pathsexist = False
            traceback.print_exc()
        return pathsexist
    
    
    
    def createspec(self):
        
        aplocation = "'"+os.path.abspath('AccessPoints').encode('string-escape')+"'"
        iconlocation = "'"+os.path.abspath('tank.ico').encode('string-escape')+"'"
        
        fh = open('TANC.spec', 'w')
        fh.write("# -*- mode: python -*-\nimport PyInstaller.utils.hooks\n\n")    
        fh.write("hiddenimports = ["+self.exval+","+self.cache+","+self.tz+"] + \\\n\
PyInstaller.utils.hooks.collect_submodules("+self.mibs+") +\\\n\
PyInstaller.utils.hooks.collect_submodules("+self.instances+") + \\\n\
PyInstaller.utils.hooks.collect_submodules('pysmi') +\\\n\
PyInstaller.utils.hooks.collect_submodules('AccessPoints')\n\n\
block_cipher = None\n\n\n")
        fh.write("a = Analysis(['WirelessTesting.py'],\n\
              pathex=["+aplocation+",\n\
              "+self.pysnmp_path+","+self.dateutil_path+",\n\
              "+aplocation+"],\n\
              binaries=None,\n\
              hiddenimports=hiddenimports,\n\
              hookspath=[],\n\
              runtime_hooks=[],\n\
              excludes=[],\n\
              win_no_prefer_redirects=False,\n\
              win_private_assemblies=False,\n\
              cipher=block_cipher)\n\
x = Tree("+self.mibs_path+",prefix='pysnmp\\\\smi\\\\mibs',excludes='.py')\n\
y = Tree("+self.pysmi_path+",prefix='pysmi',excludes='.py')\n\
z = Tree("+self.dateutil_path+",prefix='tz',excludes='.py')\n\
w = Tree("+aplocation+",prefix='AccessPoints',excludes='.py')\n\
pyz = PYZ(a.pure, a.zipped_data,\n\
             cipher=block_cipher)\n")
        fh.write("exe = EXE(pyz,\n\
        a.scripts,\n\
        a.binaries,\n\
        a.zipfiles,\n\
        w,x,y,z,\n\
        a.datas,\n\
        name='TANC',	\n\
        debug=False,\n\
        strip=False,\n\
        upx=True,\n\
        console=True,\n\
        icon="+iconlocation+"\n\
        )")
        return True
        
    def compile(self):
        if not os.path.isfile('make.bat'):
            fh = open('make.bat', 'a')
            fh.write("pyinstaller --onefile --icon=.\\tank.ico .\\TANC.spec .\\WirelessTesting.py")
            fh.close()
        os.system("make.bat")



if __name__ == '__main__':
    exe = createExe()  
    if exe.checkrequirements() and exe.setmodulespaths():
        if exe.createspec():
            exe.compile()