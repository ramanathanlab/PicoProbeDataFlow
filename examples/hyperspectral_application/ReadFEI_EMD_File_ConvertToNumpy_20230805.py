
#if __name__ == '__main__':
#
#-------------------------------------------------------------------
# Version -  Comments
#-------------------------------------------------------------------
# 2017101101 -   Initial Version 
#              reads Images
# 2018011802 -   Reads Image MetaData
# 2018011903 -   Reads Spectra and MetaData
# 2018012004 -   Reads SpectrumImage Params, but not SI
# 2018012105 -   Reads SpectrumStream Events  (very slowly!!)
# 2018012206 -   numpy Arrays instead of Python Lists - speeds things up
# 2018012907 -   fix number of pixels read error  and Y/N input flags
# 2018042108 -   add dialog box for file open
# 2018042109 -   update array definitions dialog box for file open
#2018042310  -   full text version to read parameters this is only a tem verion
#2018042311  -   parser created to format MetaData  but it is not yet used
#2018042512  -   fixed dialog box close with a pause, & labels of graphics. 
#2018042713  -   unkown modfications.relative to 12
#2014042714  -   Try to fix the data import from " multi-frame images"
#2018042715  -   for multi-frame Images  add them all up to create the composite
#2018042816 -    Misc clean up, refresh figures, comment out MetaData Printing 
#                this data is stored in the Variable list and available there for now.
#2018042817  -   rotate the imported images by 90!
#2018042818  -   canceled rotation display now matched Velox, will rotate other images instead
#                also try to speed up HyperCube creation!
#2018042919 -    Fix XY column read/store problem  Yand X  were swapped in HyperCube
#                this was due to the way the data was stored in the Stream it was YvsX not XvsY
#2018042920 -    Try to speed up the HyperDataCube creation process 
#                change how sum spectrum is created
#20w8043021 -    debugging verion playing with HCube loop for speed test 
#20w8043022 -    corrected Yaxis error in V021 by reverting to V019 loops in HCData 
#2018043023 -    corrected HCData 
#2018050124 -    add auto save of HSI Data cube to numpy file
#2018050225 -    add writing a dictionary of parameters when a numpy file is written
#2018050426 -    ? unknown update now sure if I did something here or not
#2018050427 -    comment out some of the on-screen info text, this is now captured in a Parameter Array anyway
#2018051328 -    update directory open
#2018060529 -    update Param_Mem MetaData output  - write npy Backup File now always occurs by default
#2018060730 -    change array dimensions to float16 & 32  instead of float 64
#                using current technology it is very unlikely that a HSI data set
#                will have more than 65K 2^^16 counts in a given pixel or a spectrum will 
#                have more than 2^^32 counts in a channel   phyton default is 64 bit
#                which creates huge arrays and data files and slows things down! 
#2019041831 -    some minor cleanup's  defaults to 32 bit data now. 
# This program is used to read FEI-EMD file from the Velox DAQ program
# it is NOT very good, but it works well enough to test if data is readable.
#2019042332 -    some minor cleanup's  defaults to 64 bit default on all numpy files  now. 

#
#-------------------------------------------------------------------
# strart  off with the various Python import libraries/functions
#
# import required libraries
import csv
import sys
import time
import scipy as sc
import numpy as np
from numpy import ndarray 
from scipy import ndimage, misc
from scipy.ndimage import gaussian_filter,uniform_filter
import json
import h5py  # hdf 5 file library

import matplotlib.pyplot as plt
#from mpl_toolkits.mplot3d import axes3d
#offsfrom matplotlib.widgets import Slider, Button, RadioButtons

plt.ion()  # this turns on interactive mode in matplotlib

#this routine implements  a dialog box to get the data file
def openfile_dialog(DataDirPath, fileextension):
    from PyQt5 import QtGui
    from PyQt5 import QtGui, QtWidgets
#    app = QtWidgets.QApplication([dir])  ,---This line must be commented out otherwise program locks up
    fname = QtWidgets.QFileDialog.getOpenFileName(None, "Select a file...", DataDirPath, filter="*."+str(fileextension))#filter="All files (*)")
    return str(fname[0])
#-------------------------------------------------------------------------
#code starts here
#-------------------------------------------------------------------------
    
# Version Record
NJZCode_Version="2019042332"
plt.rcParams['toolbar'] = 'toolbar2'  # this line hides the graphics tool bar from the menu

# some info on the screen

print('\n\n\n\n')
print('*******************************************************************')
print('HyperSpectral Data Read Program for FEI-EMD Files- Version: ', NJZCode_Version)
print('*******************************************************************')

print ('Be patient! This is a slow program  ;-)')

#
# definitions
#
# I am going to plot some data so I'm zeroing some arrays

TotalChannelMax=4100 # a default value
HideZeroStrobe="True" # another default
ZeroStrobeWidth=100 #anotherdefault
SDataX_Mem=np.zeros(TotalChannelMax,dtype="float32")  # create an empty Energy list for energy (x) axis
SDataY_Mem=np.zeros(TotalChannelMax,dtype="float32")  # create an empty Energy list for energy (x) axis
SImage_Mem=np.zeros((1,1),dtype="float32") # create an empty SI 2D Array
#HSImage_Mem=np.zeros((3,3,3)) # create an empty HSI 3D array
#SImage=np.zeros(shape=(2,2), dtype="float", )
SData=[0] # create a Intensity List 
Spectrum_Data_Dimensions=TotalChannelMax
#Spectrum_Data_Dimensions[0]=TotalChannelMax# this is a default value

#UserName='Nestor'
#Instrument='FEI Talos 200X'
#Specimen='Some Talos Data Files'



try: #this is a simple test routine  to see if a Path Exists
	DataDirPath
except NameError as err:
	DataDirPath="./"

    
    
print ('\nSelect FEI-Velox (.emd) File')

# Open and Read FEI-EMD file which is the format of a pseudo hdf5 file
# uisng the h5py python scripts

FileName=openfile_dialog(DataDirPath, "emd")
plt.pause(2)  # this to give the program some time to catchup. this is needed for the dialog box to close

#inputfile = open (FileName,'r')


# these are some test files. To save me writing a GUI for file names

#yFileName='ManchesterData.emd'
#FileName='Gracie0001.emd'
#FileName='Manchester-201801291454SI.emd'
#FileName='VeloxTest-41Frames-640x640-NiAl.emd'
#FileName='VeloxTest-298Frames-77x226.emd'#small data set but lots of frames
#FileName='VeloxTest-20180122-SI 512x512.emd'
#BAD-FileName='VeloxTest-1Frame-2Kx2K-9Maps-SumSpectra.emd' #this is a test file which we are working on
#FileName='VeloxTest-2Frame-2Kx2K-9Maps-SumSpectra.emd' #this is a test file which we are working on
#FileName='VeloxTest-50 Frames-1kx1K.emd'
#FileName='VeloxTest-60Frame-9Maps-SumSpectra.emd" 

# alternately uncomment next line to enter a filename

#FileName = input ('\nEnter FEI-EMD Filename : ') 

inputfile = h5py.File(FileName, "r")   # this is the local file reference name

#
# now strip out the name components
FileSName=str.split(FileName,"/")
FNlength=len(FileSName)-1  # file name should be the last element 
FLen=len(FileName)
DLen=FileName.rfind("/")
dwidth=FLen-DLen
Directory=FileName.rjust(dwidth)
DirPath=FileName.rstrip(FileSName[FNlength])

print (FileName,'\n', FileSName,'\n',FLen,'\n', DLen,'\n', Directory,'\n', DirPath)

#
#create a dictionary for file parameters
#
Param_Mem={} # a blank dictionary for temporary use
Param_Mem["FullFileName"]=FileName
Param_Mem["FShortName"]=FileSName[FNlength]
Param_Mem["Format"]='FEI Velox'

print('\n\n\n Short FileName:',FileSName[FNlength], "\n")

#close (FileName)  #this closes the dialog box
#inputfile = h5py.File(FileName, "r") #this continues the program



# find all group names in the file and print them out

print ('This HDF5 file contains multiple data groups')
print ('---------------------------\n')
print ('List of Groups in Input File: ',FileSName,'\n')
print ('----------------------------')

AllGroupNames = [n for n in inputfile.keys()]  # this uses a h5py functionality
print ("\nGroupNames in the File = ", len(AllGroupNames), "\n")

# now print  out the All the Group Names

for n in AllGroupNames:
	print(n)

# I know there are subgroups already from HDF%Viewer Program so lets look at each
DataSubGroup = inputfile['Data']  # this is the FEIEMD DATA



# make a list of the Subgroups

DataSubGroupList=[n for n in DataSubGroup.keys()]


print ('\n\n---------------------------------------')
print ('Contents of DataSubGroup', DataSubGroup)
print ('---------------------------------------')
print ('\n++++++++++++++++\n','DataGroupSubList', DataSubGroupList,'\n++++++++++++++++')
print ("The number SubGroups in DataGroup =", len(DataSubGroupList), "\n")


#now print out the List of SubGroups in the Data Group out

for n in DataSubGroupList:
        print (n)

print('----------------------------------')
print ("\n Next lets get some of the information out about the datafile")

print ("We know this is a Velox EMD file and that some things exist ")
print ("so let's get them and print them on screen\n\n")

print ("This is information about the Velox Program used to acquire the data\n")
# get the version of Velox file and print it out it is one of the main Groups

# this is stored in JSON format as a string.



print('\n----------------------------------')
print(' Experiment  ')
print('----------------------------------')

# look to see if the Experiment exists - on a crash/broken file it won't
# 
try: #this is a simple test routine  to see if a Group Exists
    indexExperiment=AllGroupNames.index ('Experiment')
    print ('Experiment Group exists')

    Experiment=inputfile['Experiment']
    Experiment_text = json.loads(Experiment.value[0].decode('utf-8'))
    print ('Experiment Info :',Experiment_text)
    ExperimentLog=inputfile["Data"]["Text"]
    ExperimentLogList=[n for n in ExperimentLog.keys()]
    print ("Number of Text Logs", len(ExperimentLogList))

except AttributeError as err:
    print ('Experiment Group does not Exist Skipping This section')

#print('    Experiment = ', str(Experiment.value))


print('\n----------------------------------')
print(' Velox Info   ')
print('----------------------------------')

try: #this is a simple test routine  to see if a Group Exists
    indexVersion=AllGroupNames.index ('Version')
    print ('Version Group exists')

    fileversion = inputfile.get('Version')
    fileversion_dict=dict()
#    fileversion_text = json.loads(fileversion.value[0].decode('utf-8'))
    fileversion_dict = json.loads(fileversion.value[0].decode('utf-8'))
#    print ('Velox File Version :',fileversion_text )#['version'])
    for keys,values in fileversion_dict.items():
            print (keys,"=",values)
    Param_Mem["DataFileVersion"]= fileversion_dict['version']
    Param_Mem["DataFileFormat"]=fileversion_dict['format']

#    ans=input ('\nPrint Application Version Info? Y = default N  :')
#
#    if ans != 'N' and ans !='n' :
#        applicationversioninfo = inputfile.get('Info')
#        applicationversion_text = json.loads(applicationversioninfo.value[0].decode('utf-8'))
#        print ('Velox Application Info :',applicationversion_text)# ['applicationVersion'])
#

except AttributeError as err:
    print ('Version Group does not Exist Skipping This section')




#
#print('----------------------------------')
#print(' Velox DisplayLayout   ')
#print('----------------------------------')
#DisplayLayout=inputfile['Application']['Velox']['DisplayLayout']
#DisplayLayout_Text= json.loads(DisplayLayout.value[0].decode('utf-8'))
#for keys,values in DisplayLayout_Text.items():
#    print (keys,"=",values)
#print ("Velox DisplayLayout_Text =", DisplayLayout_Text)
#print('    DisplayLayout = ', str(DisplayLayout.value))

#print('\n\n')
#ans=input('Velox Program Info  - Enter to continue :' )
#print('\n\n')



#stop ---- $$$$$$$ -----  here. 




#now print out the List of SubGroups in the Data-Image Group out
print('\n\n')
print('*******************************************************************')
print('  DataSubGroup-[Image]   ')
print('*******************************************************************')

Image_Data_Dimensions =[0,0,0]

try: #this is a simple test routine  to see if a Group Exists
    indexVersion=DataSubGroupList.index ('Image')
    print ('Image SubGroup exists')


    DataSubGroupImage = inputfile['Data']['Image']
    DataSubGroupImageList=[n for n in DataSubGroupImage.keys()]

    print ("  Number of Images =", len(DataSubGroupImage),'\n')
    Image_Data_Dimensions =[0,0,0]
    tempindex=1 # simple counter to keep tabs on the progress





# output each image to the screen as a graphic this loops through all images

    for nList in DataSubGroupImageList:
 
    # iterates and draws each image in the DataSubGroupImageList
        print('\n    Image Data  ')
        print('    ----------------------------------')
        print ("    ImageID - ",tempindex,":", nList) # dumps some info to the screen 
        Image_Data = inputfile['Data']['Image'][nList]['Data']
#    print('   ',Image_Data)
        Image_Data_Dimensions=Image_Data.shape
        Image_Data_Attributes=Image_Data.attrs
        print ('    Image Dimensions',Image_Data_Dimensions)
        print ('    Image Attributes',Image_Data_Attributes)
    
  
#   this draws each of the  above images but it does not store them individually
#   prepare the data for drawing
#    SImage=Image_Data[0:2048,0:2048,0] <--- notice it only draws [x,y,0]the first image of a multi-dimensional dataset

        if Image_Data_Dimensions[2] != 0:
                print ('    Note: This is a ',Image_Data_Dimensions[2],'Frame image')
                # print image metadata only for a multiframe images
                print('\n    Image MetaData   ')
                print('    ----------------------------------')
                Image_MetaData = inputfile['Data']['Image'][nList]['Metadata'][:].T[0]
                Image_MetaData_Dimensions=Image_MetaData.shape
 
    # build the metadata descriptor from the group... this is strange but it works for now
    # just convert ASCII to a character and append it to variable
#               MetaData_Text="" # erase the world first then fill it. 
#                for index in range (0,60000) :  # 60000 from HDF5 inspection
#                    MetaData_Text=MetaData_Text+(chr(Image_MetaData.value[index,0]))
#                print (MetaData_Text)
                Image_MetaData_Text=Image_MetaData.tostring().decode("utf-8")
                Image_MetaData_Dict=json.loads(Image_MetaData_Text.rstrip('\x00'))  #\x00 is a NULL


                Param_Mem['Instrument']=Image_MetaData_Dict['Instrument']['InstrumentClass']
                Param_Mem['AcceleratingVoltage']=Image_MetaData_Dict['Optics']['AccelerationVoltage']
                Param_Mem['AcceleratingVoltageUnits']='V' #FEI instruments list this in Volts not kV
                Param_Mem['SpotSize']=Image_MetaData_Dict['Optics']['SpotIndex']
                Param_Mem['PixelSize']=Image_MetaData_Dict['BinaryResult']['PixelSize']['width']
                Param_Mem['PixelUnits']=Image_MetaData_Dict['BinaryResult']['PixelUnitX']
                #
                #
                Param_Mem['ScreenCurrent']=Image_MetaData_Dict['Optics']['LastMeasuredScreenCurrent']
                Param_Mem['HolderXPosition']=Image_MetaData_Dict['Stage']['Position']["x"]
                Param_Mem['HolderYPosition']=Image_MetaData_Dict['Stage']['Position']["y"]
                Param_Mem['HolderZPosition']=Image_MetaData_Dict['Stage']['Position']["z"]
                Param_Mem['HolderAlphaTilt']=Image_MetaData_Dict['Stage']['AlphaTilt']
                Param_Mem['HolderBetaTilt']=Image_MetaData_Dict['Stage']['BetaTilt']
                Param_Mem['StageType']=Image_MetaData_Dict['Stage']['HolderType']
                Param_Mem['STEMMag']=Image_MetaData_Dict['CustomProperties']['StemMagnification']['value']
                Param_Mem['PixelSize']=Image_MetaData_Dict['BinaryResult']['PixelSize']['width']
                Param_Mem['PixelSize']=Image_MetaData_Dict['BinaryResult']['PixelSize']['width']
                Param_Mem['PixelUnits']=Image_MetaData_Dict['BinaryResult']['PixelUnitX']
#                
#                for keys,values in Image_MetaData_Dict.items():
#                   print (keys, '=',values)
#               The MetaData is in the Variable Declaration, this printing is not needed for now, just comment it out                 
#                if Image_Data_Dimensions[2] >1:    
#                    for keys2,values2 in Image_MetaData_Dict['Core'].items():
#                        print ('Core:',keys2,"=", values2)
#                    print('\n')
#                    for keys3,values3 in Image_MetaData_Dict['Instrument'].items():
#                        print ('Instrument:',keys3,"=", values3)
#                    print('\n')
#                    for keys4,values4 in Image_MetaData_Dict['Acquisition'].items():
#                        print ('Acquisition:',keys4,"=", values4)
#                    print('\n')
#                    for keys5,values5 in Image_MetaData_Dict['Optics'].items():
#                        if keys5 != "Apertures":
#                            print ('Optics:',keys5,"=", values5)
#                        else:
#                            print("in optics testing for apertures")
#                            for keys16,values16 in Image_MetaData_Dict['Optics']['Apertures']['Aperture-0'].items() :
#                                print ('Optics-Aperture-0:',keys16,"=", values16)
#                            for keys16,values16 in Image_MetaData_Dict['Optics']['Apertures']['Aperture-1'].items() :
#                                print ('Optics-Aperture-1:',keys16,"=", values16)
#                            for keys16,values16 in Image_MetaData_Dict['Optics']['Apertures']['Aperture-2'].items() :
#                                print ('Optics-Aperture-2:',keys16,"=", values16)
#                            for keys16,values16 in Image_MetaData_Dict['Optics']['Apertures']['Aperture-3'].items() :
#                                print ('Optics-Aperture-3:',keys16,"=", values16)
#                    print('\n')
#                    for keys6,values6 in Image_MetaData_Dict['EnergyFilter'].items():
#                        print ('EnergyFilter:',keys6,"=", values6)
#                    print('\n')
#                    for keys7,values7 in Image_MetaData_Dict['Stage'].items():
#                        print ('Stage:',keys7,"=", values7)
#                    print('\n')
#                    for keys8,values8 in Image_MetaData_Dict['Scan'].items():
#                        print ('Scan:',keys8,"=", values8)
#                    print('\n')
#                    for keys9,values9 in Image_MetaData_Dict['Vacuum'].items():
#                        print ('Vacuum:',keys9,"=", values9)
#                    print('\n')
#    #                for keys10,values10 in Image_MetaData_Dict['Detectors'].items():
#    #                    print ('Detectors:',keys10,"=", values10)
#    #                for keys11,values11 in Image_MetaData_Dict['Sample'].items():
#    #                    print ('Sample:',keys11,"=", values11)
#    #                for keys12,values12 in Image_MetaData_Dict['GasInjectionSystems'].items():
#    #                    print ('GasInjectionSystems:',keys12,"=", values12)
#    #                print('\n')
#    #                for keys13,values13 in Image_MetaData_Dict['Detectors'].items():
#    #                    print ('Detectors:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-0'].items():
#                        print ('Detector-0:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-1'].items():
#                        print ('Detector-1:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-2'].items():
#                        print ('Detector-2:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-3'].items():
#                        print ('Detector-3:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-4'].items():
#                        print ('Detector4:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-5'].items():
#                        print ('Detector-5:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-6'].items():
#                        print ('Detector-6:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-7'].items():
#                        print ('Detector-7:',keys13,"=", values13)
#                    for keys13,values13 in Image_MetaData_Dict['Detectors']['Detector-8'].items():
#                        print ('Detector-8:',keys13,"=", values13)
#                    print('\n')
#                    for keys14,values14 in Image_MetaData_Dict['CustomProperties'].items():
#                        print ('CustomProperties:',keys14,"=", values14)
                    
#                Now read in the data array from HDF ... note it is in a 16bit integer format!

                SImageFrame=np.array(Image_Data[0:Image_Data_Dimensions[0],0:Image_Data_Dimensions[1],0],dtype=np.float32)
                SImage=SImageFrame
                 #SImageFrame=Image_Data[0:Image_Data_Dimensions[0],0:Image_Data_Dimensions[1],0]
                if Image_Data_Dimensions[2] > 1:   # if there are multiple frames add them up
                    for index in range(1,Image_Data_Dimensions[2]-1):
                        imagemin=0
                        imagemax=0
                        SImageFrame=np.array(Image_Data[0:Image_Data_Dimensions[0],0:Image_Data_Dimensions[1],index],dtype=np.float32)
#                        SImageFrame.dtype(float)# the input array is Integer unit16 must convert it here
                        #imagemin=np.amin(SImageFrame)
                        #imagemax=np.amax(SImageFrame)
                        imagemin2=np.amin(SImage)
                        imagemax2=np.amax(SImage)

                        SImage = SImage + SImageFrame
                        plt.pause(0.05)  # just time to read things
                        print ("\r    Frame ",index,'-',round(index*100/(Image_Data_Dimensions[2]-1),3),'%', end='\r')#, "Intensity Limits : ", imagemin2, imagemax2, end='\r')
#                    FigureTemp= plt.figure(num="temp",figsize=(4,3))
#                    plt.axes([0,0,1,1]) # makes this full scale to figsize
#                    plt.xticks([]), plt.yticks([])  # this turns off tick marks
#                    plt.imshow(Temp,interpolation='nearest',cmap='bone', origin='lower') # what to plot 
#                    plt.colorbar(shrink=.8) #intensity bar on the side smaller than the figure
#                plt.show()
#                plt.pause(2) # this allows screen to catchup with python graphics



        imagemin=np.amin(SImage)
        imagemax=np.amax(SImage)
        print ("    Frame ",Image_Data_Dimensions[2], "Intensity Limits : ", imagemin, imagemax)
        if int(Image_Data_Dimensions[2]) > 2 : # this was a multi-frame image do you want to store it?
            ans="y" #input("Create Hyperspectral Image  Backup File (Default=Y), N : ")
            if ans == "Y" or ans =='y' or ans == '':
                print("\n**** Creating a Backup Image as : \n     ",FileSName[FNlength]+"-HSImage.npy"," \n**** This will be slow ****")
                np.save(FileName+"-HSImage", SImage)
                #
                #also write the Parameter Dictionary File
                #
                ParamFile=open (FileName+'-HSImage.npy.dict','w')
                ParamFile.write (json.dumps(Param_Mem))
                ParamFile.close()

        figname=str(FileSName[FNlength])+" : Image-"+str(tempindex)+" : "+str( nList)
#        SImage=Image_Data[0:Image_Data_Dimensions[0],0:Image_Data_Dimensions[1],0]    
        SImageFigure1= plt.figure(num=figname,figsize=(4,3))
#        SImage=sc.misc.imrotate(SImage,90)  # need to rotate this as the origin is funky
        np.transpose(SImage,(1,0)) #this swaps the X&Y Axii for display purposes
        plt.clf()
        plt.axes([0,0,1,1]) # makes this full scale to figsize
        plt.xticks([]), plt.yticks([])  # this turns off tick marks
        plt.imshow(SImage,cmap='gray', origin='upper') # what to plot note origin is funky 
        plt.colorbar(shrink=.8) #intensity bar on the side smaller than the figure
        plt.show()
        plt.pause(0.05) # this allows screen to catchup with python graphics

#        plt.show() # draw it\
        tempindex=tempindex+1

#now print out the List of SubGroups in the Data-Spectrum Group out
    print('\n\n')
#    ans=input(' Enter to continue to Spectrum:' )
#    print('\n\n')

except ValueError as err:
    # no image found  zero the dimensions
    print ('Image SubGroup does not Exist Skipping This section')

plt.show() # draw it
print('*******************************************************************')
print('  DataSubGroup-[Spectrum]   ')
print('*******************************************************************')


try: #this is a simple test routine  to see if a Group Exists
    indexSpectrum=DataSubGroupList.index ('Spectrum')
    print ('Spectrum SubGroup exists')


    DataSubGroupSpectrum = inputfile['Data']['Spectrum']
    DataSubGroupSpectrumList=[n for n in DataSubGroupSpectrum.keys()]

    print ("    Number of Spectra =", len(DataSubGroupSpectrumList),'\n')
    tempindex=1 # simple counter to keep tabs on the progress

# now iterate through all the spectra included

    for nList in DataSubGroupSpectrumList:
        print ("    Spectrum ID-",tempindex,":", nList) # dumps some info to the screen 


        print('')
        print('    Spectrum Data   ')
        print('----------------------------------')
        Spectrum_Data = inputfile['Data']['Spectrum'][nList]['Data']
        print('   ',Spectrum_Data)
        Spectrum_Data_Dimensions=Spectrum_Data.shape
        print ('    Spectrum Dimensions',Spectrum_Data_Dimensions)
        Spectrum_Data_Attributes=list(Spectrum_Data.attrs)
        print ('    SD Attributes: ', Spectrum_Data_Attributes )


        print('\n    Spectrum MetaData   ')
        print('    ----------------------------------')
        Spectrum_MetaData = inputfile['Data']['Spectrum'][nList]['Metadata'][:].T[0]
        Spectrum_MetaData_Dimensions=Spectrum_MetaData.shape
 
    # build the metadata descriptor from the group... this is strange but it works for now
    # just convert ASCII to a character and append it to variable
#               MetaData_Text="" # erase the world first then fill it. 
#                for index in range (0,60000) :  # 60000 from HDF5 inspection
#                    MetaData_Text=MetaData_Text+(chr(Image_MetaData.value[index,0]))
#                print (MetaData_Text)
        Spectrum_MetaData_Text=Spectrum_MetaData.tostring().decode("utf-8")
        Spectrum_MetaData_Dict=json.loads(Spectrum_MetaData_Text.rstrip('\x00'))  #\x00 is a NULL
#                
        #for keys,values in Spectrum_MetaData_Dict.items():
        #    print (keys, '=',values)

##               The MetaData is in the Variable Declaration, this printing is not needed for now, just comment it out                 
#
#
#        for keys2,values2 in Spectrum_MetaData_Dict['Core'].items():
#            print ('Core:',keys2,"=", values2)
#        print('\n')
#        for keys3,values3 in Spectrum_MetaData_Dict['Instrument'].items():
#            print ('Instrument:',keys3,"=", values3)
#        print('\n')
#        for keys4,values4 in Spectrum_MetaData_Dict['Acquisition'].items():
#            print ('Acquisition:',keys4,"=", values4)
#        print('\n')
#        for keys5,values5 in Spectrum_MetaData_Dict['Optics'].items():
#            if keys5 != "Apertures":
#                print ('Optics:',keys5,"=", values5)
#            else:
#                print("in optics testing for apertures")
#                for keys16,values16 in Spectrum_MetaData_Dict['Optics']['Apertures']['Aperture-0'].items() :
#                    print ('Optics-Aperture-0:',keys16,"=", values16)
#                for keys16,values16 in Spectrum_MetaData_Dict['Optics']['Apertures']['Aperture-1'].items() :
#                    print ('Optics-Aperture-1:',keys16,"=", values16)
#                for keys16,values16 in Spectrum_MetaData_Dict['Optics']['Apertures']['Aperture-2'].items() :
#                    print ('Optics-Aperture-2:',keys16,"=", values16)
#                for keys16,values16 in Spectrum_MetaData_Dict['Optics']['Apertures']['Aperture-3'].items() :
#                    print ('Optics-Aperture-3:',keys16,"=", values16)
#        print('\n')
#        for keys6,values6 in Spectrum_MetaData_Dict['EnergyFilter'].items():
#            print ('EnergyFilter:',keys6,"=", values6)
#        print('\n')
#        for keys7,values7 in Spectrum_MetaData_Dict['Stage'].items():
#            print ('Stage:',keys7,"=", values7)
#        print('\n')
#        for keys8,values8 in Spectrum_MetaData_Dict['Scan'].items():
#            print ('Scan:',keys8,"=", values8)
#        print('\n')
#        for keys9,values9 in Spectrum_MetaData_Dict['Vacuum'].items():
#            print ('Vacuum:',keys9,"=", values9)
#        print('\n')
#
#        for keys9,values9 in Spectrum_MetaData_Dict['BinaryResult'].items():
#            print ('BinaryResult:',keys9,"=", values9)
#        print('\n')
##                for keys10,values10 in Spectrum_MetaData_Dict['Detectors'].items():
##                    print ('Detectors:',keys10,"=", values10)
##                for keys11,values11 in Spectrum_MetaData_Dict['Sample'].items():
##                    print ('Sample:',keys11,"=", values11)
##                for keys12,values12 in Spectrum_MetaData_Dict['GasInjectionSystems'].items():
##                    print ('GasInjectionSystems:',keys12,"=", values12)
##                print('\n')
##                for keys13,values13 in Spectrum_MetaData_Dict['Detectors'].items():
##                    print ('Detectors:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-0'].items():
#            print ('Detector-0:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-1'].items():
#            print ('Detector-1:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-2'].items():
#            print ('Detector-2:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-3'].items():
#            print ('Detector-3:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-4'].items():
#            print ('Detector4:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-5'].items():
#            print ('Detector-5:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-6'].items():
#            print ('Detector-6:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-7'].items():
#            print ('Detector-7:',keys13,"=", values13)
#        for keys13,values13 in Spectrum_MetaData_Dict['Detectors']['Detector-8'].items():
#            print ('Detector-8:',keys13,"=", values13)
#        print('\n')
#        for keys14,values14 in Spectrum_MetaData_Dict['CustomProperties'].items():
#            print ('CustomProperties:',keys14,"=", values14)
#            

#print(Spectrum_MetaData.value)

#print("Spectrum Data =\n", Spectrum_Data.value)

# define the plot  now that we have the information
# this is a spectrum so let's store parameters found

        Param_Mem['Instrument']=Spectrum_MetaData_Dict['Instrument']['InstrumentClass']
        Param_Mem['AcceleratingVoltage']=Spectrum_MetaData_Dict['Optics']['AccelerationVoltage']
        Param_Mem['AcceleratingVoltageUnits']='V' #FEI instruments list this in Volts not kV
        Param_Mem['SpotSize']=Spectrum_MetaData_Dict['Optics']['SpotIndex']
        #
        #
        Param_Mem['ScreenCurrent']=Spectrum_MetaData_Dict['Optics']['LastMeasuredScreenCurrent']
        Param_Mem['HolderXPosition']=Spectrum_MetaData_Dict['Stage']['Position']["x"]
        Param_Mem['HolderYPosition']=Spectrum_MetaData_Dict['Stage']['Position']["y"]
        Param_Mem['HolderZPosition']=Spectrum_MetaData_Dict['Stage']['Position']["z"]
        Param_Mem['HolderAlphaTilt']=Spectrum_MetaData_Dict['Stage']['AlphaTilt']
        Param_Mem['HolderBetaTilt']=Spectrum_MetaData_Dict['Stage']['BetaTilt']
        Param_Mem['StageType']=Spectrum_MetaData_Dict['Stage']['HolderType']
        Param_Mem['STEMMag']=Spectrum_MetaData_Dict['CustomProperties']['StemMagnification']['value']

        #Define the location for information about the Detectors in the  System
        #Param_Mem['XEDSDetectorType']=Spectrum_MetaData_Dict['Detectors']
        # Next find the XEDS detector metadata. This can be in any "Detector" location 
        # so we just itereate the list of Detectors-N until we  find the XEDS system
        DetectorDir=Spectrum_MetaData_Dict['Detectors']
        DetectorIndex=0
        DetectorMetaDataValue=DetectorDir["Detector-"+str(DetectorIndex)]
        print ("DetectorMetaDataValue = ", DetectorMetaDataValue)
        while  DetectorMetaDataValue['DetectorType']!="AnalyticalDetector":
            DetectorMetaDataValue=DetectorDir["Detector-"+str(DetectorIndex)]
            print (DetectorIndex, "Detector-"+str(DetectorIndex), DetectorMetaDataValue['DetectorName'], DetectorMetaDataValue['DetectorType'])  # check this to make sure it is correct. 
            DetectorIndex=DetectorIndex+1 # it wasn't the XEDS detector so increement and try the next
            DetectorMetaDataValue=DetectorDir["Detector-"+str(DetectorIndex)]
        # okay in theory we get here because we found the Analytical Detector Index
        print (DetectorIndex, "Detector-"+str(DetectorIndex), DetectorMetaDataValue['DetectorName'], DetectorMetaDataValue['DetectorType'])  # check this to make sure it is correct. 
        Param_Mem['XEDSDisperion']=DetectorMetaDataValue['Dispersion']
        Param_Mem['XEDSOffsetEnergy']=DetectorMetaDataValue['OffsetEnergy']
#        Param_Mem['XEDSRealTime']=DetectorMetaDataValue['RealTime']
#        Param_Mem['XEDSLiveTime']=DetectorMetaDataValue['LiveTime']
        Param_Mem['XEDSAzimuthAngle']=DetectorMetaDataValue['AzimuthAngle']
        Param_Mem['XEDSCollectionAngle']=DetectorMetaDataValue['CollectionAngle']
        Param_Mem['XEDSElevationAngle']=DetectorMetaDataValue['ElevationAngle']

  


#the x-axis for the spectrum in channels
    chnmax=int(Spectrum_Data_Dimensions[0])
    print ("Max channel info =", chnmax, Spectrum_Data_Dimensions[0],Spectrum_Data_Dimensions[1])
    evch=5 # this should be read from the metadata it will change with instrument
    zerochannelenergyoffset=-479.0021 # these should be read from the metadata it will change with instrument
    zeroenergychanneloffset=int(abs(zerochannelenergyoffset)/evch)+10
#    Energymax=20.# 20 keV for this test program. 

#store the parameters
    
    Param_Mem["NChannels"]=int(float(chnmax)) # safety factor if "."
    Param_Mem["XUnits"]="eV"
    Param_Mem["YUnits"]="Counts"
    Param_Mem["XIncrement"]=evch
    Param_Mem["XOffset"]=float(zerochannelenergyoffset)
    Param_Mem["DataType"]="XEDS"
    



    for index in range (0,chnmax-1) :  # this loop simply fills the Energy (X axis array)
       EnergyValue=(index*evch + zerochannelenergyoffset)/1000. # keV
       SDataX_Mem[index]=EnergyValue; 
# this y-axis for the spectrum 
    SDataY_Mem=Spectrum_Data[0:chnmax]

    chanzerostrobe = int((-Param_Mem["XOffset"])/Param_Mem["XIncrement"])
    if HideZeroStrobe == "True":
        ZeroStrobeShift=int(ZeroStrobeWidth/Param_Mem["XIncrement"])# want to move at least 100eV 
    chanzerostrobe=int(chanzerostrobe+ ZeroStrobeShift)  # move 5 channels off zero strobe channel
    Ymax=1.1*np.amax(SDataY_Mem[chanzerostrobe:chnmax])

    #Ymax=1.1*max(Spectrum_Data[zeroenergychanneloffset:chnmax])
#    YMax=1.1*max(HyperSpectrumSumData[ZeroEnergyChannel:MaxEnergyChannel])

# plot the spectrum in the default Mem#0  for now just counts versus channel 
    # clear the parameter file and update it
    
    
#    CYmin=0#input('Y Axis Minimum Counts: ')
#    CYmax=1.1*np.amax(SDataY_Mem[zeroenergychanneloffset:chnmax]) #start at an offset from E=0 to skip zero channel counts
#    CYMin=float(CYmin)
#    CYMax=float(CYmax)
#    
#    EXMin=float(0)
#    EXMax=np.amax(SDataX_Mem[0:chnmax])
#    EnergyMaxDisplay=EXMax
#    if EXMax < 40:
#        EnergyMaxDisplay=40.001
#    if EXMax < 30:
#        EnergyMaxDisplay=30.001
#    if EXMax < 20:
#        EnergyMaxDisplay=20.001
#    if EXMax < 15:
#        EnergyMaxDisplay=15.001
#    if EXMax < 10:
#        EnergyMaxDisplay=10.001
#    if EXMax < 5:
#        EnergyMaxDisplay=5.001
#    if EXMax < 2:
#        EnergyMaxDisplay=2.001
#    if EXMax < 1:
#        EnergyMaxDisplay=EXMax+0.001  
#    xstep=int(EnergyMaxDisplay)/10
#
#    
#    Param_Mem0.clear()
#    Param_Mem0.update(Param_Mem) # copy temp into Mem
#    for index in range (0,chnmax):
#        SDataX_Mem0[index]=SDataX_Mem[index]
#        SDataY_Mem0[index]=SDataY_Mem[index]
#    plt.sca(WorkingplotMem0) # set the current axes 
#    plt.cla() # erase what is there
#    WorkingplotMem0.plot(SDataX_Mem0, SDataY_Mem0) # now replot it.
#    plt.title("Mem #0:" + str(FileSName[FNlength]))
#    plt.ylim(CYMin, CYMax)
#    plt.xlim(EXMin,EnergyMaxDisplay)
#    plt.xticks(np.arange(EXMin,EnergyMaxDisplay+xstep,step=xstep))
##    plt.annotate ("Mem 0:"+str(FileSName[FNlength]), xy=(0.7, 0.19), xycoords='figure fraction')
#    plt.xlabel("Energy (keV)")
#    plt.ylabel("Counts")
#    plt.show()
#    plt.pause(2)  # this to give the program some time to catchup. 
#
#    
    
#    SpectrumGraphFigure2= plt.figure(num="EMD-StoredSpectrum-Figure ",figsize=(4,3))
#    plt.plot(SDataX_Mem, SDataY_Mem)
#    plt.title("FEI Velox Spectral Data")
#    plt.ylabel('Intensity')
#    plt.xlabel('Energy-keV')
#    plt.ylim(0,Ymax)  # This is abitrary max so that I can see the data
#    plt.xlim(0,SDataX_Mem[channelmax-1])   # Generally 4096 channels of dat
#    plt.show() # draw it
    tempindex=tempindex+1
    
    print('\n\n')
#    ans=input(' Enter to continue to Spectrum-Image :' )
#    print('\n\n')

except ValueError as err:
    print ('Spectrum SubGroup does not Exist Skipping This section')

#now print out the List of SubGroups in the Data-SpectrumImage Group out

print('*******************************************************************')
print('DataSubGroup-[Spectrum-Image]   ')
print('*******************************************************************')


try: #this is a simple test routine  to see if a Group Exists
    indexSpectrumImage=DataSubGroupList.index ('SpectrumImage')
    print ('SpectrumImage SubGroup exists')


    DataSubGroupSpectrumImage = inputfile['Data']['SpectrumImage']
    DataSubGroupSpectrumImageList=[n for n in DataSubGroupSpectrumImage.keys()]


    print ("Number of Spectrum-Images =", len(DataSubGroupSpectrumImageList),'\n')

# now iterate through all the spectra included

    tempindex=1 # simple counter to keep tabs on the progress

    for nList in DataSubGroupSpectrumImageList:
        print (nList) # dumps some info to the screen 



        print('')
        print('   Spectrum-Image Data   ')
        print('----------------------------------')
        Spectrum_Image_Data = inputfile['Data']['SpectrumImage'][nList]['Data']
        print('   ',Spectrum_Image_Data)
        Spectrum_Image_Data_Dimensions=Spectrum_Image_Data.shape
        print ('    SpectrumImage Dimensions',Spectrum_Image_Data_Dimensions)
        Spectrum_Image_Data_Attributes=list(Spectrum_Image_Data.attrs)
        print ('SID Attributes: ', Spectrum_Image_Data_Attributes )
#print("Spectrum Image Data =\n", Spectrum_Image_Data.value)
        print('')
        print('    Spectrum-Image Settings   ')
        print('    ----------------------------------')
        Spectrum_ImageSettings = inputfile['Data']['SpectrumImage'][nList]['SpectrumImageSettings']
        print('   ',Spectrum_ImageSettings)
#print ('Spectrum ImageSettings Value=\n',str(Spectrum_ImageSettings.value))

        print ('    SpectrumImage MetaData Dimensions',Spectrum_Image_Data_Dimensions)
#print(SpectrumImage_MetaData.value)




    print('\n\n')
#    ans=input(' Enter to continue to Spectrum-Stream :' )
#    print('\n\n')

except ValueError as err:
    #del Image_Data_Dimension # there are no images you have to delete it first as it is a tuple
    #Image_Data_Dimension =(0,0,0)
    print ('SpectrumImage SubGroup does not Exist Skipping This section')


#now print out the List of SubGroups in the Data-SpectrumImage Group out

print('*******************************************************************')
print('DataSubGroup-[SpectrumStream]   ')
print('*******************************************************************')


try: #this is a simple test routine  to see if a Group Exists
    indexSpectrumStream=DataSubGroupList.index ('SpectrumStream')
    print ('SpectrumStream SubGroup exists')

    DataSubGroupSpectrumStream = inputfile['Data']['SpectrumStream']
    DataSubGroupSpectrumStreamList=[n for n in DataSubGroupSpectrumStream.keys()]


    print ("Number of SpectrumStream Records, =", len(DataSubGroupSpectrumStreamList),'\n')

# now iterate through all the spectra included

    tempindex=1 # simple counter to keep tabs on the progress

    for nList in DataSubGroupSpectrumStreamList:
        print ('SpectrumStream-ID : ', nList) # dumps some info to the screen 



        print('')
        print('   Spectrum-Stream Data   ')
        print('----------------------------------')
        Spectrum_Stream_Data = inputfile['Data']['SpectrumStream'][nList]['Data']
        print('   ',Spectrum_Stream_Data)
        Spectrum_Stream_Data_Dimensions=Spectrum_Stream_Data.shape
        print ('    SpectrumStream Dimensions',Spectrum_Stream_Data_Dimensions)
        Spectrum_Stream_Data_Attributes=list(Spectrum_Stream_Data.attrs)
        print ('    SSD Attributes: ', Spectrum_Stream_Data_Attributes )
#print("Spectrum Image Data =\n", Spectrum_Image_Data.value)
        print('')
        print('    Spectrum-Stream Settings   ')
        print('    ----------------------------------')
        Spectrum_StreamSettings = inputfile['Data']['SpectrumStream'][nList]['AcquisitionSettings']
        print('   ',Spectrum_StreamSettings)
#print ('Spectrum ImageSettings Value=\n',str(Spectrum_ImageSettings.value))

#        print ('    SpectrumStream MetaData Dimensions',Spectrum_Stream_Data_Dimensions)
#print(SpectrumImage_MetaData.value)




# Assume that the image dimensions of the images are the same as the Spectrum-Image

# Read a value from the Spectrum Stream Data Image
# The value will be  a channel number for which a Count(i.e. an event) has occured. 
# The value supplied is the channel  to which the count should be added. 
# If the value is 65535, this is a flag that says to increment the channel number and
# read the next value. i

    try:
        XDimension=Image_Data_Dimensions[0]
        YDimension=Image_Data_Dimensions[1]
        ZDimension=Spectrum_Data_Dimensions[0] # this is the number of channels in a spectrum
    except ValueError as err:
        print ('XDimension, YDimension, ZDimension : ', XDimension, YDimension, ZDimension)
        XDimension = input ('Enter value for XDimension: ')
        YDimension = input ('Enter value for YDimension: ')
        ZDimension = input ('Enter value for ZDimension: ')
        Spectrum_Data_Dimensions[0]=ZDimension
        
    
# Stream Spectral Data can be made up of many frames each frame is a complete Spectrum Image
    XYZFrameNumber=0 # this is just a frame counter to keep track of where we are
    XPixel=0
    YPixel=0      
    tempindex=0
    print ('\nStream Data Info = XDimension, YDimension, ZDimension, Events:',XDimension, YDimension, ZDimension, Spectrum_Stream_Data_Dimensions[0])

    start = time.time()  # measuring the elasped time with this
    Data=np.zeros(Spectrum_Stream_Data_Dimensions[0],dtype=np.uint16) #create an zero array for the Stream Data
    end0=time.time()
    print ('\nWarning: you are converting ', len(Data), 'Data events this will take time')
    print ('Elapsed Time #0 Create Data Array = ', (end0-start)/60, ' minutes')


#pyData=[0]*Spectrum_Stream_Data_Dimensions[0] # create a temporary array
#pyData[0:Spectrum_Stream_Data_Dimensions[0]] = Spectrum_Stream_Data[0:Spectrum_Stream_Data_Dimensions[0],0]
    end1=time.time()

#print ('Elapsed Time #1 Create pyData Array = ', (end1-end0)/60, ' minutes')


#    ans=input('Ready to continue  ? Y =default or N : ')
#
#   note if there are no images then you can't have stream data
#
    
    ans="Y"       
    if ans != ('N' and 'n' ):
        print ('\nGo for a walk !! This will take awhile in Python\n')
        print ('\n')
        print ('Converting Velox EMD Stream Data\n')
        if ans != ('N' and 'n' ) :

            # this reads the stream data which is a single 1D array of events 
            
            Data= Spectrum_Stream_Data[0:Spectrum_Stream_Data_Dimensions[0],0]#fill the array
#            Data[0:Spectrum_Stream_Data_Dimensions[0]]= Spectrum_Stream_Data[0:Spectrum_Stream_Data_Dimensions[0],0]#fill the array
            #print ('Preview of Data\n',Data[0:100])
            #print ('Data Length', len(Data), ' Entries')

#    Data.astype(uint16) # convert to integer array
    EventPixels = np.count_nonzero(Data==65535)  # count the pixel advance flags this should be equal to the number of points* Frames
    FramePixels = XDimension*YDimension # this is suppose to be the number of pixel in one Frame
    if (Image_Data_Dimensions[0]==0 ) or (Image_Data_Dimensions[1]==0):
        Frames=0
    else:
        Frames = EventPixels/(Image_Data_Dimensions[0]*Image_Data_Dimensions[1]) # this should be an integer
    print ('\nPixels in the Data Cube = ', XDimension, ' x ', YDimension, ' x ',ZDimension ,' = ', XDimension*YDimension*ZDimension )
    print ('Signal Events in Stream File = ', EventPixels,'\nTotal Events in Stream File = ',Spectrum_Stream_Data_Dimensions[0],'\nFrames in Stream File = ', Frames )

    end2=time.time() # measuring the elasped time with this
    print ('Elapsed Time #2 to Count the Pixels = ', (end2-end1), ' seconds\nClosing the raw data file')

    plt.pause(1)
#    close(FileName)
#for event in Spectrum_Stream_Data:   # this reads the data file
#    Data.append(event)
#    print ('File Size',len(Data), event)




    Frames = int(Frames+0.1)
    
    # check to see if there is a HSI data set by looking for frames if there are none then quit
    # otherwise create both a HSI Data Cube and a SUM spectrum
    if Frames ==0 :
        FirstFrame=0
    
    LastFrame=0

    if Frames !=0:
        print ('\nThere are ', Frames, ' Frames in this file')
        FirstFrame=1
        ansStartFrame=input('Enter Start Frame you want to convert  (Exit=0, Otherwise Start @ Frame Number): ')
# this routine simply creates a Sum of  "spectral data" from each pixel in the Data. 
#It creates at the moment just a large single spectrum.  This is a very slow routine 
        if ansStartFrame == '' or ansStartFrame == str(Frames) :
            FirstFrame=1
            if ansStartFrame == str(Frames):
                LastFrame=Frames
                print('\nStart Frame = Total Frames => All Frames were selected - Processing\n')
        else:
            FirstFrame=int(ansStartFrame)
            if FirstFrame > 0 and LastFrame == 0:
                ansLastFrame=input('Enter Last Frame you want to convert  (Default = '+ str(Frames) + '): ')
            if ansLastFrame == '' :
                LastFrame = Frames
            else:
                LastFrame = int(ansLastFrame)
            
        
            print ("\nCreating  a TotalArea-Sum-Spectra from ", FirstFrame,'-',LastFrame, "  Frames .... \nThis will be slow!!!! Be patient\n\n\n")

        #ans=input('Non-Zero Frames - Enter to Continue :')

    #nprint(LastFrame, " Sum Spectrum Stream Frame(s) Requested  ")
    

#    print ("Data Array type:", Data.dtype, Data.shape, Data.ndim)
    HyperCubeData=np.zeros((XDimension,YDimension,ZDimension)) # this is our data cube 
#    HyperCubeData=np.zeros((XDimension,YDimension,ZDimension),dtype="float16") # this is our data cube 16 bit write fails!!!
    HyperSpectrumSumData=np.zeros(4096) #  data array for the sum spectrum array 
    HyperSpectrumEnergy=np.zeros(4096) # initialize the Energy Axis array for the sum spectrum array
    XYZFrameNumber=0 # startcounting frames of data
    

#this works but it is slow
    
    for event in Data:   # this converts the Stream Data File into a HyperCube data file 640x640x41 test = 1.5 minutes
            channel=int(event)
            if XYZFrameNumber == LastFrame:
                print("Last Frame :",  XYZFrameNumber, 'of ', LastFrame, "(",Frames,")")
                break #this ends the loop afer the Nth Frame.
            if channel != 65535: # we have a real signal event  65535 means move to the next channel
                if XYZFrameNumber >= FirstFrame-1:
                    HyperSpectrumSumData[channel] += 1  # add a count to the event channel this is a SUM spectrum
                    HyperCubeData[XPixel,YPixel,channel] += 1 #This adds one count to the spectrum Channel at Xpixel,Ypixel
            else:
#            if channel == 65535: # we have a pixel increment flag not an signal event
                    if YPixel < YDimension:  # Note:  the data in teh input array is Y vs X  not X vs Y (C vs Fortan style??)
                        YPixel +=1
                    if YPixel == YDimension:
                        YPixel =0 #we are at the x limit so reset X increment Y
                        XPixel +=1
                    #print ("Frame, Line :", XYZFrameNumber, YPixel)
                    if XPixel == XDimension: #we are at the Y limit reset Y increment Frame
                        XPixel=0
                        XYZFrameNumber +=1
                        if XYZFrameNumber < FirstFrame:
                            print ("\rFrame :", XYZFrameNumber, ' skipped', end='\r') # this is a simple counter to show progress
                        else :
                            print ("\rFrame :", XYZFrameNumber,'of',LastFrame, "(",Frames, ') -',round(XYZFrameNumber*100/LastFrame,2),'%', end='\r') # this is a simple counter to show progress
  
#this has an error in the y axis somewhere but it is faster

#    for event in Data:   # this converts the Stream Data File into a HyperCube data file
#
#            if XYZFrameNumber == LastFrame:
#                print("Last Frame :",  XYZFrameNumber)
#                break #this ends the loop afer the Nth Frame.
#            if event != 65535: # we have a real signal event  65535 means move to the next channel
##            HyperSpectralImage[XPixel,YPixel,event]+=1  # add one count to signal channel 
#                channel = int(event)
#                if XYZFrameNumber >= FirstFrame-1:
#                    HyperSpectrumSumData[channel] += 1  # add a count to the event channel this is a SUM spectrum
#                    HyperCubeData[XPixel,YPixel,channel] += 1 #This adds one count to the spectrum Channel at Xpixel,Ypixel
##                    HyperSpectrumSumData[channel]= HyperSpectrumSumData[channel] +1  # add a count to the event channel this is a SUM spectrum
##                    HyperCubeData[XPixel,YPixel,channel]= HyperCubeData[XPixel,YPixel,channel] +1 #This adds one count to the spectrum Channel at Xpixel,Ypixel
#            #print ('Frame:',XYZFrameNumber, XPixel,YPixel,event, channel, )
#
#            else:
##            if event == 65535: # we have a pixel increment flag not an signal event
#                    if YPixel < YDimension:  # Note:  the data in teh input array is Y vs X  not X vs Y (C vs Fortan style??)
#                        YPixel +=1
#                    if YPixel == YDimension:
#                        YPixel =0 #we are at the x limit so reset X increment Y
#                        XPixel +=1
#                    #print ("Frame, Line :", XYZFrameNumber, YPixel)
#                    if XPixel == XDimension: #we are at the Y limit reset Y increment Frame
#                        XPixel=0
#                        XYZFrameNumber +=1
#                        if XYZFrameNumber < FirstFrame:
#                            print ("Frame :", XYZFrameNumber, ' skipped') # this is a simple counter to show progress
#                        else :
#                            print ("Frame :", XYZFrameNumber) # this is a simple counter to show progress
##                    if XPixel < XDimension:
##                        XPixel +=1
##                    if XPixel == XDimension:
##                        XPixel =0 #we are at the x limit so reset X increment Y
##                        YPixel +=1
##                    #print ("Frame, Line :", XYZFrameNumber, YPixel)
##                    if YPixel == YDimension: #we are at the Y limit reset Y increment Frame
##                        YPixel=0
##                        XYZFrameNumber +=1
##                        if XYZFrameNumber < FirstFrame:
##                            print ("Frame :", XYZFrameNumber, ' skipped') # this is a simple counter to show progress
##                        else :
##                            print ("Frame :", XYZFrameNumber) # this is a simple counter to show progress
#                        

#   for ichan in (0,Spectrum_Data_Dimensions[0]-1):
#   compute the sum spectrum over the entire XY axis
#    HyperSpectrumSumData=np.sum(HyperCubeData,axis=(0,1)) # this should sum spectrum over the entire array
    end3=time.time() # measuring the elasped time with this
    print ('\nElapsed time to create HSI Sum Spectra =', (end3-end2)/60, ' minutes\n', len(Data)/(100000*(end3-end2)) , " MegaEvents/sec")
#    close(FileName)                    
    if (LastFrame!=0): # only draw if there are Frames read and  stored
    #the x-axis for the spectrum in channels

    #
    # store DataCube as numpyfile if it has been created
    #
        ans="Y"#input("Create HyperDataCube  File (Default=Y), N : ")
        if ans == "Y" or ans =='y' or ans == '':
            end4=time.time()
            print("\n**** Creating a Backup HSI Data Cube as : \n     ",FileSName[FNlength]+'-'+str(FirstFrame) +'-'+str(LastFrame)+"Frames-HSDataCube_64bit.npy"," \n**** This will be slow ****")
            np.save(FileName+"-"+str(FirstFrame) +'-'+str(LastFrame)+"Frames-HSDataCube_64bit", HyperCubeData)
            #
            #also write the Parameter Dictionary File
            #
            ParamFile=open (FileName+'-'+str(FirstFrame) +'-'+str(LastFrame)+'Frames-HSDataCube_64bit.npy.dict','w')
            ParamFile.write (json.dumps(Param_Mem))
            ParamFile.close()
            end5=time.time()
            #print (Param_Mem)
            print ('Elapsed Time to create backup files = ', (end5-end4)/60 , ' minutes')
        channelmax=int(Spectrum_Data_Dimensions[0])
        
        
        ZeroEnergyChannel=int((-Param_Mem["XOffset"])/Param_Mem["XIncrement"])
        # get off of the strobe peak at channel zero
        MaxEnergyChannel=int(ZDimension)



        # find the zero strobe channel
        chanzerostrobe0 = int((-Param_Mem["XOffset"])/Param_Mem["XIncrement"])
        if HideZeroStrobe == "True":
            ZeroStrobeShift=int(ZeroStrobeWidth/Param_Mem["XIncrement"])# want to move at least strobe width 
            chanzerostrobe0=int(chanzerostrobe0+ ZeroStrobeShift)  # move 5 channels off zero strobe channel      
        if ZeroEnergyChannel < chanzerostrobe0:
                ZeroEnergyChannel=chanzerostrobe0
 

        YMax=1.1*np.amax(HyperSpectrumSumData[ZeroEnergyChannel:MaxEnergyChannel])
        YMin=np.amin(HyperSpectrumSumData[ZeroEnergyChannel:MaxEnergyChannel])

#    print ("Max channel info =", channelmax, Spectrum_Data_Dimensions[0],Spectrum_Data_Dimensions[1])
        evch=Param_Mem["XIncrement"] # this should be read from the metadata it will change with instrument
        zerochannelenergyoffset=Param_Mem["XOffset"] # these should be read from the metadata it will change with instrument
 #       Energymax=20.# 20 keV for this test program. 
        for index in range (0,channelmax-1) :
            EnergyValue=(index*evch + zerochannelenergyoffset)/1000. # keV
            HyperSpectrumEnergy[index]= EnergyValue; # index should be multipled by ev/channel + zerochannelenergyoffset
# plot the spectrum  for now just counts versus channel 

        EXMin=float(0)
        EXMax=EnergyValue
        EnergyMaxDisplay=EXMax
        if EXMax < 40:
            EnergyMaxDisplay=40.001
        if EXMax < 30:
            EnergyMaxDisplay=30.001
        if EXMax < 20:
            EnergyMaxDisplay=20.001
        if EXMax < 15:
            EnergyMaxDisplay=15.001
        if EXMax < 10:
            EnergyMaxDisplay=10.001
        if EXMax < 5:
            EnergyMaxDisplay=5.001
        if EXMax < 2:
            EnergyMaxDisplay=2.001
        if EXMax < 1:
            EnergyMaxDisplay=EXMax+0.001  
        xstep=int(EnergyMaxDisplay)/10




        HyperSpectrumSumFigure= plt.figure(num="EMD-HSCube-SumSpectrum-Figure",figsize=(6,4.5))
        plt.cla()
        plt.plot(HyperSpectrumEnergy[ZeroEnergyChannel:MaxEnergyChannel-1], HyperSpectrumSumData[ZeroEnergyChannel:MaxEnergyChannel-1])
        plt.xticks(np.arange(EXMin, EXMax, step=xstep))  # this turns off tick marks
        plt.title(str(FileSName[FNlength])+" :\n "+str(FirstFrame) +'-'+str(LastFrame)+" Frame(s) Sum Spectrum")
        plt.ylabel('Counts')
        plt.xlabel('Energy-keV')
        if YMin <=0 : YMin=0.1
        plt.yscale('log') # the data range can be huge  try log plot 
        plt.ylim(YMin,YMax)  # This is abitrary max so that I can see the data
        plt.xlim(0,EnergyMaxDisplay)   # Generally 4096 channels of data
        plt.show() # draw it

# all done
        
    
    
except ValueError as err:
    print ('SpectrumStream SubGroup does not Exist Skipping This section')
    
#
# this routine is finished close the file
#
#close(FileName)
print('\n\nHyperSpectral Data Cube created! Use HSImage Extract program to Visualize Data Slices')
    
print('\n\n')
print('*******************************************************************')
print('Script End   ')
print('*******************************************************************\n\n')
                                                  