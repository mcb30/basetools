import Ffs
import AprioriSection
from GenFdsGlobalVariable import GenFdsGlobalVariable
import os
import subprocess
from CommonDataClass.FdfClassObject import FvClassObject

T_CHAR_LF = '\n'

class FV (FvClassObject):
    def __init__(self):
        FvClassObject.__init__(self)
        self.FvInfFile = None
        self.BaseAddress = None
        
    #
    #  Generate Fv and add it to the Buffer
    #
    def AddToBuffer (self, Buffer, BaseAddress=None, BlockSize= None, BlockNum=None, ErasePloarity='1', VtfDict=None) :
        self.__InitialInf__(BaseAddress, BlockSize, BlockNum, ErasePloarity, VtfDict)
        #
        # First Process the Apriori section
        #
        GenFdsGlobalVariable.VerboseLogger('First generate Aprioris file !')
        if not (self.AprioriSection == None):
            FileNameList = self.AprioriSection.GenFfs ()
            #
            # Add Apriori section included Ffs file name to Inf file
            #
            for Ffs in FileNameList :
                self.FvInfFile.writelines("EFI_FILE_NAME = " + \
                                           Ffs               + \
                                           T_CHAR_LF)
        #
        # Process Modules in FfsList
        #
        for FfsFile in self.FfsList :
            FileName = FfsFile.GenFfs()
            self.FvInfFile.writelines("EFI_FILE_NAME = " + \
                                       FileName          + \
                                       T_CHAR_LF)
            
        self.FvInfFile.close()
        #
        # Call GenFv tool
        #
        
        FvOutputFile = os.path.join(GenFdsGlobalVariable.FvDir, self.UiFvName)
        FvOutputFile = FvOutputFile + '.Fv'
        cmd = 'GenFv -i '                 + \
               self.InfFileName           + \
               ' -o '                     + \
               FvOutputFile
        #
        # Call GenFv Tools
        #
        GenFdsGlobalVariable.CallExternalTool(cmd, "GenFv Failed!")
        #
        # Write the Fv contents to Buffer
        #
        fv = open ( FvOutputFile,'r+b')
                   
        GenFdsGlobalVariable.InfLogger( "Generate %s Fv Successfully" %self.UiFvName)
              
        Buffer.write(fv.read())
        fv.close
        return FvOutputFile
    
    def __InitialInf__ (self, BaseAddress = None, BlockSize= None, BlockNum = None, ErasePloarity='1', VtfDict=None) :
        self.InfFileName = os.path.join(GenFdsGlobalVariable.FvDir,
                                   self.UiFvName + '.inf')
        self.FvInfFile = open (self.InfFileName, 'w+')
        
        #
        # Add [Options]
        #
        self.FvInfFile.writelines("[options]" + T_CHAR_LF)
        if BaseAddress != None :
            self.FvInfFile.writelines("EFI_BASE_ADDRESS = " + \
                                       BaseAddress          + \
                                       T_CHAR_LF)
                                       
        if BlockSize != None and BlockNum != None:
            self.FvInfFile.writelines("EFI_BLOCK_SIZE = " + \
                                      '0x%x' %BlockSize    + \
                                      T_CHAR_LF)
            self.FvInfFile.writelines("EFI_NUM_BLOCKS   = "  + \
                                      ' 0x%x' %BlockNum    + \
                                      T_CHAR_LF)
        else:
            for BlockSize in self.BlockSizeList :
                self.FvInfFile.writelines("EFI_BLOCK_SIZE  = "  + \
                                          '0x%x' %BlockSize[0]    + \
                                          T_CHAR_LF)
                                  
                self.FvInfFile.writelines("EFI_NUM_BLOCKS   = "  + \
                                          ' 0x%x' %BlockSize[1]    + \
                                          T_CHAR_LF)
                                          
        if self.BsBaseAddress != None:
            self.FvInfFile.writelines('EFI_BOOT_DRIVER_BASE_ADDRESS = ' + \
                                       '0x%x' %self.BsBaseAddress)
        if self.RtBaseAddress != None:
            self.FvInfFile.writelines('EFI_RUNTIME_DRIVER_BASE_ADDRESS = ' + \
                                      '0x%x' %self.RtBaseAddress)
        #
        # Add attribute
        #
        self.FvInfFile.writelines("[attributes]" + T_CHAR_LF)
        
        self.FvInfFile.writelines("EFI_ERASE_POLARITY   = "       + \
                                          ' %s' %ErasePloarity    + \
                                          T_CHAR_LF)
        if not (self.FvAttributeDict == None):
            for FvAttribute in self.FvAttributeDict.keys() :
                self.FvInfFile.writelines("EFI_"            + \
                                          FvAttribute       + \
                                          ' = '             + \
                                          self.FvAttributeDict[FvAttribute] + \
                                          T_CHAR_LF )
        if self.FvAlignment != None:
            self.FvInfFile.writelines("EFI_FVB2_ALIGNMENT_"     + \
                                       self.FvAlignment.strip() + \
                                       " = TRUE"                + \
                                       T_CHAR_LF)
        #
        # Add [Files]
        #
            
        self.FvInfFile.writelines("[files]" + T_CHAR_LF)
        if VtfDict != None and self.UiFvName in VtfDict.keys():
            self.FvInfFile.writelines("EFI_FILE_NAME = "                   + \
                                       VtfDict.get(self.UiFvName)          + \
                                       T_CHAR_LF)
        



    


