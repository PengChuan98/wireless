mcl_RUDAT64.dll - 64 bit COM Object for programmers under 64 bit operating system

This DLL file can be used by programmers of Microsoft Visual Studio (Visual Basic, C#, Visual C++)
or any other program that recognize 64 bit com DLL file.

mcl_RUDAT.dll file should be loaded to the project as a reference file.

The DLL file include the following Functions:

1. int Connect(Optional *string SN)  :

SN parameter is needed in case of using more than 1 Device.
SN is the Serial Number of the Device and can be ignored if using only one box.

2. void Disconnect()

Recommended to Disconnect the device while end of program

3. int Read_ModelName(string ModelName) As Integer
The Model Name returned in ModelName parameter.

4. int Read_SN(string SN ) 
The Serial Number returned in SN parameter.

5. int SetAttenuation( float TotalAtt) 

TotalAtt - parameter for the required Attenuation
return 1 for success or  0 for software failure

6. int Read_Att( float CAtt1 )

Read the current Attenuation
CAtt1 - will be returned with the current attenuation.
The function return 1 on success , 0 for fail.

  
7. Int Get_Available_SN_List(string SN_List)

string SN_List is returned with all available Devices connected to USB.
the function return the Number of Devices.
   
8. GetExtFirmware -returns the internal firmware version of the attenuator 

9. GetUSBConnectionStatus - return the USB Connection Status.

10. Set_Address -sets the internal address of the attenuator connected via USB
  
11. Get_Address -returns the USB address of the connected attenuator

12. Set_StartUpAttIndicator - Parameter for start up index  
-----Asc("F") - fixed ,attenuation should be defined by Set_StartUpAtt
-----Asc("L") - the last attenuation (Note: Initiate Store Last Attenuation or close the GUI before disconnecting the attenuator's DC supply in order to remember the  state )
-----Asc("N"), other - the attenuation is not defined, will be maximum default
   
13. Set_StartUpAtt - Parameter for start up attenuation ,
prior it , should be set start up index: as "F"- Fixed

14. Get_StartUpAttIndicator - Returns start up index

15. Get_StartUpAtt - Returns start up attenuation


16. InitiateStoreLastAtt() - Initiate store of the Last Attenuation. 
                            return 1 on success
                           
17. int Send_SCPI(string SndSTR , string RetSTR )                              

              Send SCPI command/Query - return 1 on success


18 Ethernet Functions - available only for RCDAT models!

	GetEthernet_CurrentConfig
        GetEthernet_IPAddress
        GetEthernet_MACAddress
        GetEthernet_NetworkGateway
        GetEthernet_PWD
        GetEthernet_SubNetMask
        GetEthernet_TCPIPPort
        GetEthernet_TELNETPPort     // in firmware C7 and above
        GetEthernet_UseDHCP
        GetEthernet_UsePWD
        SaveEthernet_IPAddress
        SaveEthernet_NetworkGateway
        SaveEthernet_PWD
        SaveEthernet_SubnetMask
        SaveEthernet_TCPIPPort
        SaveEthernet_TELNETPPort   // in firmware C7 and above
        SaveEthernet_UseDHCP
        SaveEthernet_UsePWD

19. Hop/Sweep Functons:
        int Hop_GetDirection() - returns direction of HOP (0=fw,1=bw,2=both)
        int Hop_GetMaxDwell() - return maximum allowed dwell time
        int Hop_GetMinDwell() - return minimum allowed dwell time
        int Hop_GetMaxNoOfPoints() - return maximum allowed Hop points
        int Hop_GetNoOfPoints() - - return number of Hop points
        int Hop_GetPoint(int PointNo, float HopPower,int HopDwT,int HopDwTUnits )- returns for a particular point: attenuation,dwell time and unit of time (Ascii of 'u' or 'm' or 's')        
        int Hop_SetDirection(int HopDirection ) set direction of HOP (0=fw,1=bw,2=both)
        int Hop_SetMode(int onoff ) - start / stop hoping (1/0) 
        int Hop_SetNoOfPoints(int HopNoOfPoints) - set no. of hop points
        int Hop_SetPoint(int PointNo,float HopPower, int HopDwT,int HopDwTUnits) - set a point: attenuation,dwell time and unit of time (Ascii of 'u' or 'm' or 's')        

        int Sweep_GetDirection() - returns direction of Sweep (0=fw,1=bw,2=both)
        int Sweep_GetDwell() - return dwell time 
        int Sweep_GetMaxDwell() - return maximum allowed dwell time
        int Sweep_GetMinDwell() - return minimum allowed dwell time
        single Sweep_GetStartAtt() - return sweep start attenuation
        single Sweep_GetStepSize() - return sweep step size attenuation
        single Sweep_GetStopAtt() - return sweep stop attenuation
        int Sweep_SetDirection(int SweepDirection ) sets direction of Sweep (0=fw,1=bw,2=both)
        int  Sweep_SetDwell(int dwell , int dwell_units ) -  sets dwell time and unit of time (Ascii of 'u' or 'm' or 's')        
        int Sweep_SetMode(ByVal onoff As Integer) - start / stop sweeping (1/0) 
        int Sweep_SetStartAtt(ByVal Pr As Single) - sets sweep start attenuation
        int Sweep_SetStepSize(ByVal Pr As Single) - sets sweep step size attenuation
        int Sweep_SetStopAtt(ByVal Pr As Single) - sets sweep stop attenuation
        
         functions supported by 4 Channels model:
 
 1.   int Set_ChannelStartUpAtt( int Channel , int StartUpAtt ) 
      - set the start up attenuation when power up for a specific channel
 2.   int SetChannelAtt( int Channel , float TotalAtt ) 
 3.   int SetChannelsAtt(float Att1 As Single, int CH1 , int CH2, int CH3, int CH4) 
 4.   float ReadChannelAtt(int Channel) 
     - return the current Attenuation of a specific channel
 5.  int Read4ChannelsAtt(float *C1Att, float *C2Att, float *C3Att, float *C4Att) 
        read the 4 channels current attenuation
 6.  int Sweep_SetActiveChannels(int CH1_YesNO , int CH2_YesNO, int CH3_YesNO, int CH4_YesNO) 
 7.  int Sweep_GetActiveChannels(int *CH1_YesNO , int *CH2_YesNO , int *CH3_YesNO , int *CH4_YesNO) 
 8.  int Sweep_SetChannelStartAtt(int Channel , float Att )
 9.  float Sweep_GetChannelStartAtt(int Channel ) 
 10. int Sweep_SetChannelStepSize(int Channel , float Att) 
 11. float Sweep_GetChannelStepSize(int Channel) 
 12. int Sweep_SetChannelStopAtt(int Channel , float Att )
 13. float Sweep_GetChannelStopAtt(int Channel )
 14. int Hop_SetActiveChannels(int CH1_YesNO , int CH2_YesNO, int CH3_YesNO, int CH4_YesNO) 
 15. int Hop_GetActiveChannels(int *CH1_YesNO , int *CH2_YesNO , int *CH3_YesNO , int *CH4_YesNO) 
 16. int Hop_SetPoint4Channels(int PointNo, float HopAtt1, float HopAtt2, float HopAtt3, float HopAtt4, int HopDwT , int HopDwTUnits) 
 17. int Hop_GetPoint4Channels(int PointNo, float *HopAtt1, float *HopAtt2, float *HopAtt3, float *HopAtt4, string *HopDwT) 


program Example in VB:

' mcl_RUDAT64.dll should be loaded as a reference file to the project
Dim MyAtt As New mcl_RUDAT64.USB_RUDAT ,Status as integer
Status=MyAtt.Connect
Status = MyAtt.SetAttenuation(20.5)  ' set attenuation of 20.5 dB
MyAtt.Disconnect

program Example in C#:

 // mcl_RUDAT64.dll should be loaded as a reference file to the project
  mcl_RUDAT64.USB_RUDAT MyAtt = new mcl_RUDAT64.USB_RUDAT();
int Status = 0;
float SetAtt = 20.5f;
string Address = "";
Status = MyAtt.Connect(ref(Address));
Status = MyAtt.SetAttenuation(SetAtt);  // set attenuation of 20.5 dB
MyAtt.Disconnect();

program Example in Visual C++:

// mcl_RUDAT64.dll should be loaded as a reference file to the project
mcl_RUDAT64::USB_RUDAT ^MyAtt = gcnew mcl_RUDAT64::USB_RUDAT();
short Status = 0;
System::String ^SN = "";
System::String ^SW_Name1 = "A";
float ReadResult = 0;
Status = MyAtt->Connect(SN);
Status=MyAtt->SetAttenuation(20.5)  // set attenuation of 20.5 dB
MyAtt->Disconnect();




      