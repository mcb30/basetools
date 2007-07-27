from struct import *
from GenFdsGlobalVariable import GenFdsGlobalVariable
import StringIO
from Common.FdfClassObject import RegionClassObject

class region(RegionClassObject):
    def __init__(self):
        RegionClassObject.__init__(self)
        

    """Add RegionData to Fd file"""

    def AddToBuffer(self, Buffer, BaseAddress, BlockSizeList, ErasePolarity, FvBinDict, vtfDict = None):
        Size = self.Size
        GenFdsGlobalVariable.InfLogger('Generate Region')
        GenFdsGlobalVariable.InfLogger("   Region Size = %d" %Size)
        
        if self.RegionType == 'FV':
            #
            # Get Fv from FvDict
            #
            fv = GenFdsGlobalVariable.FdfParser.profile.FvDict.get(self.RegionData.upper())
            #
            # Create local Buffer
            #
            
            if fv != None :
                GenFdsGlobalVariable.InfLogger('   Region Name = Fv:%s'%self.RegionData)
                #
                # Call GenFv tool
                #
                
                self.FvAddress = int(BaseAddress, 16) + self.Offset
                BlockSize = self.__BlockSizeOfRegion__(BlockSizeList)
                BlockNum = self.__BlockNumOfRegion__(BlockSize)
                FvBaseAddress = '0x%x' %self.FvAddress
                FileName = fv.AddToBuffer(Buffer, FvBaseAddress, BlockSize, BlockNum, ErasePolarity, vtfDict)
                BinFile = open (FileName, 'r+b')
                FvBuffer = StringIO.StringIO('')
                FvBuffer.write(BinFile.read())
                if FvBuffer.len > Size:
                    raise Exception ("Size of Fv (%s) is large than Region Size ", self.RegionData)
                elif FvBuffer.len < Size :
                    raise Exception ("Size of Fv (%s) is less than Region Size ", self.RegionData)
                FvBuffer.close()
                FvBinDict[self.RegionData.upper()] = FileName

        if self.RegionType == 'FILE':
            GenFdsGlobalVariable.InfLogger('   Region Name = FILE: %s'%self.RegionData)
            BinFile = open (self.RegionData, 'r+b')
            FvBuffer = StringIO.StringIO('')
            FvBuffer.write(BinFile.read())
            if FvBuffer.len > Size :
                raise Exception ("Size of File (%s) large than Region Size ", self.RegionData)
            #
            # If File contents less than region size, append "0xff" after it
            #
            elif FvBuffer.len < Size:
                for index in range(0, (Size-FvBuffer.len)):
                    if (ErasePolarity == '1'):
                        FvBuffer.write(Pack('B', int('0xFF', 16)))
                    else:
                        FvBuffer.write(Pack('B', int('0x00', 16)))
            Buffer.write(FvBuffer)
            FvBuffer.close()
            
        if self.RegionType == 'DATA' :
            GenFdsGlobalVariable.InfLogger('   Region Name = DATA')
            Data = self.RegionData.split(',')
            if len(Data) > Size:
               raise Exception ("Size of DATA large than Region Size ")
            elif len(Data) <= Size:
                for item in Data :
                    Buffer.write(pack('B', int(item, 16)))
                if (ErasePolarity == '1'):
                    Buffer.write(pack(str(Size - len(Data))+'B', *(int('0xFF', 16) for i in range(Size - len(Data)))))
                else:
                    Buffer.write(pack(str(Size - len(Data))+'B', *(int('0x00', 16) for i in range(Size - len(Data)))))

                
        if self.RegionType == None:
            GenFdsGlobalVariable.InfLogger('   Region Name = None')
            if (ErasePolarity == '1') :
                Buffer.write(pack(str(Size)+'B', *(int('0xFF', 16) for i in range(0, Size))))
            else :
                Buffer.write(pack(str(Size)+'B', *(int('0x00', 16) for i in range(0, Size))))

    def __BlockSizeOfRegion__(self, BlockSizeList):
        Offset = 0x00
        BlockSize = 0
        for item in BlockSizeList:
            Offset = Offset + item[0]  * item[1]
            GenFdsGlobalVariable.VerboseLogger ("Offset = 0x%x" %Offset)
            GenFdsGlobalVariable.VerboseLogger ("self.Offset %x" %self.Offset)

            if self.Offset < Offset :
                BlockSize = item[0]
                GenFdsGlobalVariable.VerboseLogger ("BlockSize = %s" %BlockSize)
                return BlockSize
        return BlockSize
    
    def __BlockNumOfRegion__ (self, BlockSize):
        if BlockSize == 0 :
            raise Exception ("Region: %s doesn't in Fd address scope !" %self.Offset)
        BlockNum = self.Size / BlockSize
        GenFdsGlobalVariable.VerboseLogger ("BlockNum = %x" %BlockNum)
        return BlockNum
                
