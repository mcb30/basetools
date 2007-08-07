# Copyright (c) 2007, Intel Corporation
# All rights reserved. This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.  The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.

#
#This file is used to collect all defined strings in multiple uni files 
#

import os, codecs, re
import Common.EdkLogger
from Common.BuildToolError import *

UNICODE_WIDE_CHAR = u'\\wide'
UNICODE_NARROW_CHAR = u'\\narrow'
UNICODE_NON_BREAKING_CHAR = u'\\nbr'
UNICODE_UNICODE_CR = '\r'
UNICODE_UNICODE_LF = '\n'

NARROW_CHAR = u'\uFFF0'
WIDE_CHAR = u'\uFFF1'
NON_BREAKING_CHAR = u'\uFFF2'
CR = u'\u000D'
LF = u'\u000A'
NULL = u'\u0000'
TAB = u'\t'
BACK_SPLASH = u'\\'

gIncludePattern = re.compile("^#include +[\"<]+([^\"< >]+)[>\"]+$", re.MULTILINE | re.UNICODE)

def UniToStr(Uni):
    return repr(Uni)[2:-1]

def UniToHexList(Uni):
    List = []
    for Item in Uni:
        Temp = '%04X' % ord(Item)
        List.append('0x' + Temp[2:4])
        List.append('0x' + Temp[0:2])
    return List

class StringDefClassObject(object):
    def __init__(self, Name = None, Value = None, Referenced = False, Token = None, UseOtherLangDef = ''):
        self.StringName = ''
        self.StringNameByteList = []
        self.StringValue = ''
        self.StringValueByteList = ''
        self.Token = 0
        self.Referenced = Referenced
        self.UseOtherLangDef = UseOtherLangDef
        self.Length = 0
        
        if Name != None:
            self.StringName = Name
            self.StringNameByteList = UniToHexList(Name)
        if Value != None:
            self.StringValue = Value + u'\x00'        # Add a NULL at string tail
            self.StringValueByteList = UniToHexList(self.StringValue)
            self.Length = len(self.StringValueByteList)
        if Token != None:
            self.Token = Token

    def __str__(self):
        return repr(self.StringName) + ' ' + \
               repr(self.Token) + ' ' + \
               repr(self.Referenced) + ' ' + \
               repr(self.StringValue)

class UniFileClassObject(object):
    def __init__(self, FileList = []):
        self.FileList = FileList
        self.Token = 2
        self.LanguageDef = []                   #[ [u'LanguageIdentifier', u'PrintableName'], ... ]
        self.OrderedStringList = {}             #{ u'LanguageIdentifier' : [StringDefClassObject]  }
        
        if len(self.FileList) > 0:
            self.LoadUniFiles(FileList)

    def GetLangDef(self, Line):
        Lang = Line.split()
        if len(Lang) != 3:
            raise ParserError(msg="""Wrong language definition '""" + Line + """' which should be '#langdef eng "English"'""")
        else:
            LangName = Lang[1]
            LangPrintName = Lang[2][1:-1]

        if [LangName, LangPrintName] not in self.LanguageDef:
            self.LanguageDef.append([LangName, LangPrintName])
        
        #
        # Add language string
        #
        self.AddStringToList(u'$LANGUAGE_NAME', LangName, LangName, 0, True)
        self.AddStringToList(u'$PRINTABLE_LANGUAGE_NAME', LangName, LangPrintName, 1, True)

        return True
        
    def GetStringObject(self, Item):
        Name = ''
        Language = ''
        Value = ''
        
        Name = Item.split()[1]
        LanguageList = Item.split(u'#language ')
        for IndexI in range(len(LanguageList)):
            if IndexI == 0:
                continue
            else:
                Language = LanguageList[IndexI].split()[0]
                Value = LanguageList[IndexI][LanguageList[IndexI].find(u'\"') + len(u'\"') : LanguageList[IndexI].rfind(u'\"')].replace(u'\r\n', u'')
                self.AddStringToList(Name, Language, Value)
    
    def GetIncludeFile(self, Item, Dir):
        FileName = Item[Item.find(u'#include ') + len(u'#include ') :Item.find(u' ', len(u'#include '))][1:-1]
        self.LoadUniFile(FileName)
    
    def PreProcess(self, File):
        if not os.path.exists(File) or not os.path.isfile(File):
            raise ParserError(msg=File + ' is not a valid file')
        
        Dir = os.path.dirname(File)
        FileIn = codecs.open(File, mode='rb', encoding='utf-16').readlines()
        Lines = []
        #
        # Use unique identifier
        #
        for Line in FileIn:
            Line = Line.strip()
            #
            # Ignore comment line and empty line
            #
            if Line == u'' or Line.startswith(u'//'):
                continue
            Line = Line.replace(u'/langdef', u'#langdef')
            Line = Line.replace(u'/string', u'#string')
            Line = Line.replace(u'/language', u'#language')
            Line = Line.replace(u'/include', u'#include')
                        
            Line = Line.replace(UNICODE_WIDE_CHAR, WIDE_CHAR)
            Line = Line.replace(UNICODE_NARROW_CHAR, NARROW_CHAR)
            Line = Line.replace(UNICODE_NON_BREAKING_CHAR, NON_BREAKING_CHAR)
            Line = Line.replace(u'\\r\\n', CR + LF)
            Line = Line.replace(u'\\n', CR + LF)
            Line = Line.replace(u'\\r', CR)
            Line = Line.replace(u'\\t', u'\t')
            Line = Line.replace(u'\\\\', u'\\')
            Line = Line.replace(u'''\"''', u'''"''')
            Line = Line.replace(u'\t', u' ')
#           if Line.find(u'\\x'):
#               hex = Line[Line.find(u'\\x') + 2 : Line.find(u'\\x') + 6]
#               hex = "u'\\u" + hex + "'"
                        
            IncList = gIncludePattern.findall(Line)
            if len(IncList) == 1:
                Lines.extend(self.PreProcess(os.path.join(Dir, IncList[0])))
                continue

            Lines.append(Line)
        
        return Lines
    
    def LoadUniFile(self, File = None):
        if File == None:
            raise ParserError(ms='No unicode file is given')
        #
        # Process special char in file
        #
        Lines = self.PreProcess(File)
        
        #
        # Get Unicode Information
        #
        for IndexI in range(len(Lines)):
            Line = Lines[IndexI]
            if (IndexI + 1) < len(Lines):
                SecondLine = Lines[IndexI + 1]
            if (IndexI + 2) < len(Lines):
                ThirdLine = Lines[IndexI + 2]
                                    
            #
            # Get Language def information
            # 
            if Line.find(u'#langdef ') >= 0:
                self.GetLangDef(Line)
                continue
            
            Name = ''
            Language = ''
            Value = ''
            #
            # Get string def information format 1 as below
            #
            #     #string MY_STRING_1
            #     #language eng
            #     My first English string line 1
            #     My first English string line 2
            #     #string MY_STRING_1
            #     #language spa
            #     Mi segunda secuencia 1
            #     Mi segunda secuencia 2
            #
            if Line.find(u'#string ') >= 0 and Line.find(u'#language ') < 0 and \
                SecondLine.find(u'#string ') < 0 and SecondLine.find(u'#language ') >= 0 and \
                ThirdLine.find(u'#string ') < 0 and ThirdLine.find(u'#language ') < 0:
                Name = Line[Line.find(u'#string ') + len(u'#string ') : ].strip()
                Language = SecondLine[SecondLine.find(u'#language ') + len(u'#language ') : ].strip()
                for IndexJ in range(IndexI + 2, len(Lines)):
                    if Lines[IndexJ].find(u'#string ') < 0 and Lines[IndexJ].find(u'#language ') < 0:
                        Value = Value + Lines[IndexJ]
                    else:
                        IndexI = IndexJ
                        break
                Value = Value.replace(u'\r\n', u'')
                self.AddStringToList(Name, Language, Value)
                continue
            
            #
            # Get string def information format 2 as below
            #
            #     #string MY_STRING_1     #language eng     "My first English string line 1"
            #                                               "My first English string line 2"
            #                             #language spa     "Mi segunda secuencia 1"
            #                                               "Mi segunda secuencia 2"
            #     #string MY_STRING_2     #language eng     "My first English string line 1"
            #                                               "My first English string line 2"
            #     #string MY_STRING_2     #language spa     "Mi segunda secuencia 1"
            #                                               "Mi segunda secuencia 2"
            #
            if Line.find(u'#string ') >= 0 and Line.find(u'#language ') >= 0:
                StringItem = Line
                for IndexJ in range(IndexI + 1, len(Lines)):
                    if Lines[IndexJ].find(u'#string ') >= 0 and Lines[IndexJ].find(u'#language ') >= 0:
                        IndexI = IndexJ
                        break
                    elif Lines[IndexJ].find(u'#string ') < 0 and Lines[IndexJ].find(u'#language ') >= 0:
                        StringItem = StringItem + Lines[IndexJ]
                    elif Lines[IndexJ].find(u'\"') >= 2:
                        StringItem = StringItem[ : StringItem.rfind(u'\"')] + Lines[IndexJ][Lines[IndexJ].find(u'\"') + len(u'\"') : ]
                self.GetStringObject(StringItem)              
    
    def LoadUniFiles(self, FileList = []):
        if len(FileList) > 0:
            for File in FileList:
                self.LoadUniFile(File)
                
    def AddStringToList(self, Name, Language, Value, Token = None, Referenced = False, UseOtherLangDef = ''):
        if Language not in self.OrderedStringList:
            self.OrderedStringList[Language] = []
        
        IsAdded = False
        for Item in self.OrderedStringList[Language]:
            if Name == Item.StringName:
                IsAdded = True
                break
        if not IsAdded:
            Token = len(self.OrderedStringList[Language])
            self.OrderedStringList[Language].append(StringDefClassObject(Name, Value, Referenced, Token, UseOtherLangDef))
    
    def SetStringReferenced(self, Name):
        for Lang in self.OrderedStringList:
            for Item in self.OrderedStringList[Lang]:
                if Name == Item.StringName:
                    Item.Referenced = True
                    break
    
    def FindStringValue(self, Name, Lang):
        for Item in self.OrderedStringList[Lang]:
            if Item.StringName == Name:
                return Item
        
        return None
    
    def ReToken(self):
        #
        # Search each string to find if it is defined for each language
        # Use secondary language value to replace if missing in any one language
        #           
        for IndexI in range(0, len(self.LanguageDef)):
            LangKey = self.LanguageDef[IndexI][0]
            for Item in self.OrderedStringList[LangKey]:
                Name = Item.StringName
                Value = Item.StringValue[0:-1]
                Referenced = Item.Referenced
                for IndexJ in range(0, len(self.LanguageDef)):
                    LangFind = self.LanguageDef[IndexJ][0]
                    if self.FindStringValue(Name, LangFind) == None:
                        Token = len(self.OrderedStringList[LangFind])
                        self.AddStringToList(Name, LangFind, Value, Token, Referenced, LangKey)
        
        #
        # Retoken
        #
        for Lang in self.LanguageDef:
            LangName = Lang[0]
            ReferencedStringList = []
            NotReferencedStringList = []
            Token = 0
            for Item in self.OrderedStringList[LangName]:
                if Item.Referenced == True:
                    Item.Token = Token
                    ReferencedStringList.append(Item)
                    Token = Token + 1
                else:
                    NotReferencedStringList.append(Item)
            self.OrderedStringList[LangName] = ReferencedStringList
            for Index in range(len(NotReferencedStringList)):
                NotReferencedStringList[Index].Token = Token + Index
                self.OrderedStringList[LangName].append(NotReferencedStringList[Index])
            
# This acts like the main() function for the script, unless it is 'import'ed into another
# script.
if __name__ == '__main__':
    a = UniFileClassObject(['C:\\Tiano\\Edk\\Sample\\Universal\\UserInterface\\SetupBrowser\\Dxe\\DriverSample\\inventorystrings.uni', 'C:\\Tiano\\Edk\\Sample\\Universal\\UserInterface\\SetupBrowser\\Dxe\\DriverSample\\VfrStrings.uni'])
    print a.LanguageDef
    print a.OrderedStringList
    for i in a.OrderedStringList:
        print i
        for m in a.OrderedStringList[i]:
            print str(m)
