#test_prog_atten.py

from prog_atten import ProgAtten
import unittest
import re
from time import sleep

def stripAtten(string):
    m = re.search('Atten#',string)
    if m.group(0) != string:
        num,value = string.strip('Atten#').strip(' dB').split(' = ')
        return int(num),int(value)
    else:
        return False

class TestJFW50PA(unittest.TestCase):
    def test_OpenClose(self):
        print "in test_OpenClose"
        pa = JFW50PA(port="\\.\COM4")
        self.assertTrue(pa.Open())
        pa.Read()
        self.assertTrue(pa.Close())

    def test_attenuators(self):
        print "in test_attenuators"
        pa = JFW50PA(port="\\.\COM4")
        self.assertTrue(pa.Open())
        pa.Read()
        pa.setAttenuator(1,22,resp=True)
        pa.Send()
        pa.setAttenuator(2,23)
        pa.getAttenuator(2)
        pa.Send()
        output = pa.Read()
        num,value = stripAtten(output[0])
        self.assertEqual(num,1)
        self.assertEqual(value,22)
        num,value = stripAtten(output[1])
        self.assertEqual(num,2)
        self.assertEqual(value,23)

        pa.setMultipleAtten(3,24,4,25)
        pa.getAttenuator(3)
        pa.getAttenuator(4)
        pa.Send()
        output = pa.Read()
        self.assertEqual(output[0],"2 Attenuators Set")
        num,value = stripAtten(output[1])
        self.assertEqual(num,3)
        self.assertEqual(value,24)
        num,value = stripAtten(output[2])
        self.assertEqual(num,4)
        self.assertEqual(value,25)
        
        self.check_all_attenuators(pa,[22,23,24,25])
        
        self.assertTrue(pa.Close())

    def check_all_attenuators(self,pa,values):
        print "in check_all_attenuators"
        num = 1
        i = 0
        pa.Read()
        pa.getAllAtten()
        pa.Send()
        output = pa.Read()
        for el in output[1:]:
            output = el.strip('Atten').split()
            self.assertEqual(num,int(output[0]))
            self.assertEqual(values[i],int(output[1]))
            num = num + 1
            i = i + 1

    def test_attenuator_memory(self):
        print "in test_attenuator_memory"
        pa = JFW50PA(port="\\.\COM4")
        self.assertTrue(pa.Open())
        pa.Read()
        pa.setMultipleAtten(1,22,2,23)
        pa.setMultipleAtten(3,24,4,25)
        pa.Send()
        pa.Read()
        pa.storeAttenuators()
        pa.Send()
        output = pa.Read()
        self.assertEqual(output[0],"4 Attenuator Settings Stored In Memory")
        pa.setAttenuator(1,50)
        pa.Send()
        pa.recallAttenuators()
        pa.Send()
        output = pa.Read()
        self.assertEqual(output[0],"4 Attenuator Settings Loaded From Memory")
        self.check_all_attenuators(pa,[22,23,24,25])
        self.assertTrue(pa.Close())

    def test_pause(self):
        print "in test_pause"
        pa = JFW50PA(port="\\.\COM4")
        self.assertTrue(pa.Open())
        pa.Read()
        pa.Read()
        pa.pause(2,time='S')
        pa.Send()
        output = pa.Read()
        self.assertEqual(output[0],"Pause Started")
        sleep(4)
        output = pa.Read()
        self.assertEqual(output[0],"Pause Finished")
        self.assertTrue(pa.Close())

    def test_fade_attenuator(self):
        print "in test_fade_attenuator"
        pa = JFW50PA(port="\\.\COM4")
        self.assertTrue(pa.Open())
        pa.Read()
        pa.setFadeAtten(1,0,22,100)
        pa.Send()
        output = pa.Read()
        self.assertEqual(output[0],"Fade Started")
        sleep(3)
        output = pa.Read()
        self.assertEqual(output[0],"Fade Finished")
        self.assertTrue(pa.Close())

    def test_variable_handover(self):
        print "in test_variable_handover"
        pa = JFW50PA(port="\\.\COM4")
        self.assertTrue(pa.Open())
        pa.Read()
        pa.setVariableHandover(1,2,0,22,200)
        pa.Send()
        output = pa.Read()
        self.assertEqual(output[0],"Handover Started")
        sleep(8)
        output = pa.Read()
        self.assertEqual(output[0],"Handover Finished")
        self.assertTrue(pa.Close())

    def test_set_all_attenuators(self):
        print "test_set_all_attenuators"
        pa = JFW50PA(port="\\.\COM4")
        self.assertTrue(pa.Open())
        pa.Read()
        pa.setAllAtten(26)
        pa.Send()
        output = pa.Read()
        self.assertEqual(output[0],"Attens 1-4 = 26 dB")
        self.assertTrue(pa.Close())
        
if __name__ == '__main__':
    unittest.main()
