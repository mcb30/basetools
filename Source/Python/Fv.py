import Ffs
import AprioriSection
from GenFdsGlobalVariable import GenFdsGlobalVariable
import os
import subprocess

T_CHAR_LF = '\n'

class FV:
    def __init__(self):
        self.UiFvName = None
        self.CreateFileName = None
        # 3-tuple list (blockSize, numBlocks, pcd)
        self.BlockSizeList = []
        # DefineVarDict[var] = value
        self.DefineVarDict = {}
        # SetVarDict[var] = value
        self.SetVarDict = {}
        self.FvAlignment = None
        # FvAttributeDict[attribute] = TRUE/FALSE (1/0)
        self.FvAttributeDict = {}
##        self.FvAttributeset = None
##        self.FvAttributeClear = None
        self.AprioriSection = None
        self.FfsList = []
        
        self.FvInfFile = None
        self.BaseAddress = None
        
    #
    #  Generate Fv and add it to the Buffer
    #
    def AddToBuffer (self, Buffer, BaseAddress) :
        self.__InitialInf__(BaseAddress)
        #
        # First Process the Apriori section
        #
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
               GenFdsGlobalVariable.FvDir + \
               self.UiFvName              + \
               '.inf'                     + \
               ' -o '                     + \
               FvOutputFile
        #
        # Call GenFv Tools
        #
        print cmd
        PopenObject = subprocess.Popen(cmd)
        PopenObject.communicate()
        if PopenObject.returncode != 0 :
            raise Exception ("GenFv Failed!")
        
        #
        # Write the Fv contents to Buffer
        #
        fv = open ( FvOutputFile,'r+b')
                   
        print "Write the Fv contents to buffer"
              
        Buffer.write(fv.read())
        fv.close
    
    def __InitialInf__ (self, BaseAddress) :
        self.FvInfFile = open (GenFdsGlobalVariable.FvDir + \
                               self.UiFvName              + \
                               '.inf',                      \
                               'w+')
        #
        # Add [Options]
        #
        self.FvInfFile.writelines("[options]" + T_CHAR_LF)
        
        self.FvInfFile.writelines("EFI_BASE_ADDRESS = " + \
                                   BaseAddress          + \
                                   T_CHAR_LF)
                                   
        for BlockSize in self.BlockSizeList :
            self.FvInfFile.writelines("EFI_BLOCK_SIZE   = " + \
                                      '%s' %BlockSize[0]    + \
                                      T_CHAR_LF)
                                  
            self.FvInfFile.writelines("EFI_NUM_BLOCKS   = "  + \
                                      ' %s' %BlockSize[1]    + \
                                      T_CHAR_LF)
        
        #
        # Add attribute
        #
        self.FvInfFile.writelines("[attribute]" + T_CHAR_LF)
        
        if not (self.FvAttributeDict == None):
            for FvAttribute in self.FvAttributeDict.keys() :
                self.FvInfFile.writelines("EFI_"            + \
                                          FvAttribute       + \
                                          '='               + \
                                          self.FvAttributeDict[FvAttribute] + \
                                          T_CHAR_LF )
        if self.FvAlignment != None:
            self.FvInfFile.writelines("FVB2_ALIGNMENT_"         + \
                                       self.FvAlignment.strip() + \
                                       "= TRUE"                 + \
                                       T_CHAR_LF)
        #
        # Add [Files]
        #
            
        self.FvInfFile.writelines("[files]" + T_CHAR_LF)



    


