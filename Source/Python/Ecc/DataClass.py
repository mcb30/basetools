## @file
# This file is used to define class for data sturcture used in ECC
#
# Copyright (c) 2007, Intel Corporation
# All rights reserved. This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.    The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.

##
# Import Modules
#
import Common.EdkLogger as EdkLogger

##
# Static values for data models
#
MODEL_UNKNOWN = 0

MODEL_FILE_C = 1001
MODEL_FILE_H = 1002
MODEL_FILE_ASM = 1003
MODEL_FILE_INF = 1011
MODEL_FILE_DEC = 1012
MODEL_FILE_DSC = 1013
MODEL_FILE_DSC = 1014

MODEL_VARIABLE_FILE_HEADER = 2001
MODEL_VARIABLE_FUNCTION_HEADER = 2002
MODEL_VARIABLE_COMMENT = 2003
MODEL_VARIABLE_PARAMETER = 2004
MODEL_VARIABLE_STRUCTURE = 2005
MODEL_VARIABLE_VARIABLE = 2006
MODEL_VARIABLE_INCLUDE = 2007
MODEL_VARIABLE_MACRO = 2008
MODEL_VARIABLE_PREDICATE_EXPRESSION = 2009

MODEL_EFI_PROTOCOL = 3001
MODEL_EFI_PPI = 3002
MODEL_EFI_GUID = 3003
MODEL_EFI_LIBRARY_CLASS = 3004
MODEL_EFI_LIBRARY_INSTANCE = 3005
MODEL_EFI_PCD = 3006
MODEL_EFI_SOURCE_FILE = 3007
MODEL_EFI_BINARY_FILE = 3008

MODEL_PCD_FIXED_AT_BUILD = 4001
MODEL_PCD_PATCHABLE_IN_MODULE = 4002
MODEL_PCD_FEATURE_FLAG = 4003
MODEL_PCD_DYNAMIC_EX = 4004
MODEL_PCD_DYNAMIC = 4005

MODEL_LIST = [('MODEL_UNKNOWN', MODEL_UNKNOWN),
              ('MODEL_FILE_C', MODEL_FILE_C),
              ('MODEL_FILE_H', MODEL_FILE_H),
              ('MODEL_FILE_ASM', MODEL_FILE_ASM),
              ('MODEL_FILE_INF', MODEL_FILE_INF),
              ('MODEL_FILE_DEC', MODEL_FILE_DEC),
              ('MODEL_FILE_DSC', MODEL_FILE_DSC),
              ('MODEL_FILE_DSC', MODEL_FILE_DSC),
              ('MODEL_VARIABLE_FILE_HEADER', MODEL_VARIABLE_FILE_HEADER),
              ('MODEL_VARIABLE_FUNCTION_HEADER', MODEL_VARIABLE_FUNCTION_HEADER),
              ('MODEL_VARIABLE_COMMENT', MODEL_VARIABLE_COMMENT),
              ('MODEL_VARIABLE_PARAMETER', MODEL_VARIABLE_PARAMETER),
              ('MODEL_VARIABLE_STRUCTURE', MODEL_VARIABLE_STRUCTURE),
              ('MODEL_VARIABLE_VARIABLE', MODEL_VARIABLE_VARIABLE),
              ('MODEL_VARIABLE_INCLUDE', MODEL_VARIABLE_INCLUDE),
              ('MODEL_VARIABLE_MACRO', MODEL_VARIABLE_MACRO),
              ('MODEL_VARIABLE_PREDICATE_EXPRESSION', MODEL_VARIABLE_PREDICATE_EXPRESSION),
              ('MODEL_EFI_PROTOCOL', MODEL_EFI_PROTOCOL),
              ('MODEL_EFI_PPI', MODEL_EFI_PPI),
              ('MODEL_EFI_GUID', MODEL_EFI_GUID),
              ('MODEL_EFI_LIBRARY_CLASS', MODEL_EFI_LIBRARY_CLASS),
              ('MODEL_EFI_LIBRARY_INSTANCE', MODEL_EFI_LIBRARY_INSTANCE),
              ('MODEL_EFI_PCD', MODEL_EFI_PCD),
              ('MODEL_EFI_SOURCE_FILE', MODEL_EFI_SOURCE_FILE),
              ('MODEL_EFI_BINARY_FILE', MODEL_EFI_BINARY_FILE),
              ('MODEL_PCD_FIXED_AT_BUILD', MODEL_PCD_FIXED_AT_BUILD),
              ('MODEL_PCD_PATCHABLE_IN_MODULE', MODEL_PCD_PATCHABLE_IN_MODULE),
              ('MODEL_PCD_FEATURE_FLAG', MODEL_PCD_FEATURE_FLAG),
              ('MODEL_PCD_DYNAMIC_EX', MODEL_PCD_DYNAMIC_EX),
              ('MODEL_PCD_DYNAMIC', MODEL_PCD_DYNAMIC)
             ]

## FunctionClass
#
# This class defines a structure of a function
# 
# @param ID:               ID of a Function
# @param Header:           Header of a Function
# @param Modifier:         Modifier of a Function 
# @param Name:             Name of a Function
# @param ReturnStatement:  ReturnStatement of a Funciont
# @param StartLine:        StartLine of a Function
# @param StartColumn:      StartColumn of a Function
# @param EndLine:          EndLine of a Function
# @param EndColumn:        EndColumn of a Function
# @param BelongsToFile:    The Function belongs to which file
# @param VariableList:     VariableList of a File
# @param PcdList:          PcdList of a File
#
# @var ID:                 ID of a Function
# @var Header:             Header of a Function
# @var Modifier:           Modifier of a Function 
# @var Name:               Name of a Function
# @var ReturnStatement:    ReturnStatement of a Funciont
# @var StartLine:          StartLine of a Function
# @var StartColumn:        StartColumn of a Function
# @var EndLine:            EndLine of a Function
# @var EndColumn:          EndColumn of a Function
# @var BelongsToFile:      The Function belongs to which file
# @var VariableList:       VariableList of a File
# @var PcdList:            PcdList of a File
#
class FunctionClass(object):
    def __init__(self, ID = -1, Header = '', Modifier = '', Name = '', ReturnStatement = '', StartLine = -1, StartColumn = -1, EndLine = -1, EndColumn = -1, BelongsToFile = -1, VariableList = [], PcdList = []):
        self.ID = ID
        self.Header = Header
        self.Modifier = Modifier                    
        self.Name = Name
        self.ReturnStatement = ReturnStatement
        self.StartLine = StartLine
        self.StartColumn = StartColumn
        self.EndLine = EndLine
        self.EndColumn = EndColumn
        self.BelongsToFile = BelongsToFile
        
        self.VariableList = VariableList
        self.PcdList = PcdList

## VariableClass
#
# This class defines a structure of a variable
# 
# @param ID:                 ID of a Variable
# @param Modifier:           Modifier of a Variable
# @param Type:               Type of a Variable
# @param Name:               Name of a Variable
# @param Value:              Value of a Variable
# @param Model:              Model of a Variable
# @param BelongsToFile:      The Variable belongs to which file
# @param BelongsToFunction:  The Variable belongs to which function
# @param StartLine:          StartLine of a Variable
# @param StartColumn:        StartColumn of a Variable
# @param EndLine:            EndLine of a Variable
# @param EndColumn:          EndColumn of a Variable
#
# @var ID:                   ID of a Variable
# @var Modifier:             Modifier of a Variable
# @var Type:                 Type of a Variable
# @var Name:                 Name of a Variable
# @var Value:                Value of a Variable
# @var Model:                Model of a Variable
# @var BelongsToFile:        The Variable belongs to which file
# @var BelongsToFunction:    The Variable belongs to which function
# @var StartLine:            StartLine of a Variable
# @var StartColumn:          StartColumn of a Variable
# @var EndLine:              EndLine of a Variable
# @var EndColumn:            EndColumn of a Variable
#
class VariableClass(object):
    def __init__(self, ID = -1, Modifier = '', Type = '', Name = '', Value = '', Model = MODEL_UNKNOWN, BelongsToFile = -1, BelongsToFunction = -1, StartLine = -1, StartColumn = -1, EndLine = -1, EndColumn = -1):
        self.ID = ID
        self.Modifier = Modifier
        self.Type = Type
        self.Name = Name
        self.Value = Value
        self.BelongsToFile = BelongsToFile
        self.BelongsToFunction = BelongsToFunction
        self.StartLine = StartLine
        self.StartColumn = StartColumn
        self.EndLine = EndLine
        self.EndColumn = EndColumn

## PcdClass
#
# This class defines a structure of a Pcd
# 
# @param ID:                   ID of a Pcd
# @param CName:                CName of a Pcd
# @param TokenSpaceGuidCName:  TokenSpaceGuidCName of a Pcd
# @param Token:                Token of a Pcd
# @param DatumType:            DatumType of a Pcd
# @param Model:                Model of a Pcd
# @param BelongsToFile:        The Pcd belongs to which file
# @param BelongsToFunction:    The Pcd belongs to which function
# @param StartLine:            StartLine of a Pcd
# @param StartColumn:          StartColumn of a Pcd
# @param EndLine:              EndLine of a Pcd
# @param EndColumn:            EndColumn of a Pcd
#
# @var ID:                     ID of a Pcd
# @var CName:                  CName of a Pcd
# @var TokenSpaceGuidCName:    TokenSpaceGuidCName of a Pcd
# @var Token:                  Token of a Pcd
# @var DatumType:              DatumType of a Pcd
# @var Model:                  Model of a Pcd
# @var BelongsToFile:          The Pcd belongs to which file
# @var BelongsToFunction:      The Pcd belongs to which function
# @var StartLine:              StartLine of a Pcd
# @var StartColumn:            StartColumn of a Pcd
# @var EndLine:                EndLine of a Pcd
# @var EndColumn:              EndColumn of a Pcd
#
class PcdClass(object):
    def __init__(self, ID = -1, CName = '', TokenSpaceGuidCName = '', Token = '', DatumType = '', Model = MODEL_UNKNOWN, BelongsToFile = -1, BelongsToFunction = -1, StartLine = -1, StartColumn = -1, EndLine = -1, EndColumn = -1):
        self.ID = ID
        self.CName = CName
        self.TokenSpaceGuidCName = TokenSpaceGuidCName
        self.Token = Token
        self.DatumType = DatumType
        self.BelongsToFile = BelongsToFile
        self.BelongsToFunction = BelongsToFunction
        self.StartLine = StartLine
        self.StartColumn = StartColumn
        self.EndLine = EndLine
        self.EndColumn = EndColumn

## FileClass
#
# This class defines a structure of a file
# 
# @param ID:            ID of a File
# @param Name:          Name of a File
# @param ExtName:       ExtName of a File
# @param Path:          Path of a File
# @param FullPath:      FullPath of a File
# @param Model:         Model of a File
# @param FunctionList:  FunctionList of a File
# @param VariableList:  VariableList of a File
# @param PcdList:       PcdList of a File
#
# @var ID:              ID of a File
# @var Name:            Name of a File
# @var ExtName:         ExtName of a File
# @var Path:            Path of a File
# @var FullPath:        FullPath of a File
# @var Model:           Model of a File
# @var FunctionList:    FunctionList of a File
# @var VariableList:    VariableList of a File
# @var PcdList:         PcdList of a File
#
class FileClass(object):
    def __init__(self, ID = -1, Name = '', ExtName = '', Path = '', FullPath = '', Model = MODEL_UNKNOWN, FunctionList = [], VariableList = [], PcdList = []):
        self.ID = ID                                   
        self.Name = Name
        self.ExtName = ExtName                    
        self.Path = Path
        self.FullPath = FullPath
        self.Model = Model
        
        self.FunctionList = FunctionList
        self.VariableList = VariableList
        self.PcdList = PcdList
