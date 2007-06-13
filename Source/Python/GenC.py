#!/usr/bin/env python
import string
import EdkLogger
from DataType import *

ItemTypeStringDatabase  = {
    TAB_PCDS_FEATURE_FLAG:'FixedAtBuild',
    TAB_PCDS_FIXED_AT_BUILD:'FixedAtBuild',
    TAB_PCDS_PATCHABLE_IN_MODULE:'BinaryPatch',
    TAB_PCDS_DYNAMIC:'',
    TAB_PCDS_DYNAMIC_EX:''
}

DatumSizeStringDatabase = {'UINT8':'8','UINT16':'16','UINT32':'32','UINT64':'64','BOOLEAN':'BOOLEAN','VOID*':'8'}
DatumSizeStringDatabaseH = {'UINT8':'8','UINT16':'16','UINT32':'32','UINT64':'64','BOOLEAN':'BOOL','VOID*':'PTR'}
DatumSizeStringDatabaseLib = {'UINT8':'8','UINT16':'16','UINT32':'32','UINT64':'64','BOOLEAN':'Bool','VOID*':'Ptr'}

PcdDatabaseCommonAutoGenH = """
//
// The following definition will be generated by build tool
//

//
// Common definitions
//
typedef UINT8 SKU_ID;

#define PCD_TYPE_SHIFT        28

#define PCD_TYPE_DATA         (0x0 << PCD_TYPE_SHIFT)
#define PCD_TYPE_HII          (0x8 << PCD_TYPE_SHIFT)
#define PCD_TYPE_VPD          (0x4 << PCD_TYPE_SHIFT)
#define PCD_TYPE_SKU_ENABLED  (0x2 << PCD_TYPE_SHIFT)
#define PCD_TYPE_STRING       (0x1 << PCD_TYPE_SHIFT)

#define PCD_TYPE_ALL_SET      (PCD_TYPE_DATA | PCD_TYPE_HII | PCD_TYPE_VPD | PCD_TYPE_SKU_ENABLED | PCD_TYPE_STRING)

#define PCD_DATUM_TYPE_SHIFT  24

#define PCD_DATUM_TYPE_POINTER  (0x0 << PCD_DATUM_TYPE_SHIFT)
#define PCD_DATUM_TYPE_UINT8    (0x1 << PCD_DATUM_TYPE_SHIFT)
#define PCD_DATUM_TYPE_UINT16   (0x2 << PCD_DATUM_TYPE_SHIFT)
#define PCD_DATUM_TYPE_UINT32   (0x4 << PCD_DATUM_TYPE_SHIFT)
#define PCD_DATUM_TYPE_UINT64   (0x8 << PCD_DATUM_TYPE_SHIFT)

#define PCD_DATUM_TYPE_ALL_SET  (PCD_DATUM_TYPE_POINTER | \\
                                 PCD_DATUM_TYPE_UINT8   | \\
                                 PCD_DATUM_TYPE_UINT16  | \\
                                 PCD_DATUM_TYPE_UINT32  | \\
                                 PCD_DATUM_TYPE_UINT64)

#define PCD_DATABASE_OFFSET_MASK (~(PCD_TYPE_ALL_SET | PCD_DATUM_TYPE_ALL_SET))

typedef struct  {
  UINT32  ExTokenNumber;
  UINT16  LocalTokenNumber;   // PCD Number of this particular platform build
  UINT16  ExGuidIndex;        // Index of GuidTable
} DYNAMICEX_MAPPING;

typedef struct {
  UINT32  SkuDataStartOffset; //We have to use offsetof MACRO as we don't know padding done by compiler
  UINT32  SkuIdTableOffset;   //Offset from the PCD_DB
} SKU_HEAD;

typedef struct {
  UINT16  GuidTableIndex;     // Offset in Guid Table in units of GUID.
  UINT16  StringIndex;        // Offset in String Table in units of UINT16.
  UINT16  Offset;             // Offset in Variable
  UINT16  DefaultValueOffset; // Offset of the Default Value
} VARIABLE_HEAD;

typedef  struct {
  UINT32  Offset;
} VPD_HEAD;

typedef UINT16 STRING_HEAD;

typedef UINT16 SIZE_INFO;

#define offsetof(s,m)  (UINT32) (UINTN) &(((s *)0)->m)

"""

PcdDatabaseEpilogueAutoGenH = """
typedef struct {
  PEI_PCD_DATABASE PeiDb;
  DXE_PCD_DATABASE DxeDb;
} PCD_DATABASE;

#define PCD_TOTAL_TOKEN_NUMBER (PEI_LOCAL_TOKEN_NUMBER + DXE_LOCAL_TOKEN_NUMBER)

"""

PcdDatabaseAutoGenH = """
#define ${PHASE}_GUID_TABLE_SIZE                ${GUID_TABLE_SIZE}
#define ${PHASE}_STRING_TABLE_SIZE              ${STRING_TABLE_SIZE}
#define ${PHASE}_SKUID_TABLE_SIZE               ${SKUID_TABLE_SIZE}
#define ${PHASE}_LOCAL_TOKEN_NUMBER_TABLE_SIZE  ${LOCAL_TOKEN_NUMBER_TABLE_SIZE}
#define ${PHASE}_LOCAL_TOKEN_NUMBER             ${LOCAL_TOKEN_NUMBER}
#define ${PHASE}_EXMAPPING_TABLE_SIZE           ${EXMAPPING_TABLE_SIZE}
#define ${PHASE}_EX_TOKEN_NUMBER                ${EX_TOKEN_NUMBER}
#define ${PHASE}_SIZE_TABLE_SIZE                ${SIZE_TABLE_SIZE}
#define ${PHASE}_GUID_TABLE_EMPTY               ${GUID_TABLE_EMPTY}
#define ${PHASE}_STRING_TABLE_EMPTY             ${STRING_TABLE_EMPTY}
#define ${PHASE}_SKUID_TABLE_EMPTY              ${SKUID_TABLE_EMPTY}
#define ${PHASE}_DATABASE_EMPTY                 ${DATABASE_EMPTY}
#define ${PHASE}_EXMAP_TABLE_EMPTY              ${EXMAP_TABLE_EMPTY}

typedef struct {
${BEGIN}  UINT64             ${INIT_CNAME_DECL_UITN64}_${INIT_GUID_DECL_UINT64}[${INIT_NUMSKUS_DECL_UINT64}];
${END}
${BEGIN}  UINT64             ${VARDEF_CNAME_UINT64}_${VARDEF_GUID_UINT64}_VariableDefault_${VARDEF_SKUID_UINT64};
${END}
${BEGIN}  UINT32             ${INIT_CNAME_DECL_UINT32}_${INIT_GUID_DECL_UINT32}[${INIT_NUMSKUS_DECL_UINT32}];
${END}
${BEGIN}  UINT32             ${VARDEF_CNAME_UINT32}_${VARDEF_GUID_UINT32}_VariableDefault_${VARDEF_SKUID_UINT32};
${END}
${BEGIN}  VPD_HEAD           ${VPD_HEAD_CNAME_DECL}_${VPD_HEAD_GUID_DECL}[${VPD_HEAD_NUMSKUS_DECL}];
${END}
  DYNAMICEX_MAPPING  ExMapTable[${PHASE}_EXMAPPING_TABLE_SIZE];
  UINT32             LocalTokenNumberTable[${PHASE}_LOCAL_TOKEN_NUMBER_TABLE_SIZE];
  EFI_GUID           GuidTable[${PHASE}_GUID_TABLE_SIZE];
${BEGIN}  STRING_HEAD        ${STRING_HEAD_CNAME_DECL}_${STRING_HEAD_GUID_DECL}[${STRING_HEAD_NUMSKUS_DECL}];
${END}
${BEGIN}  VARIABLE_HEAD      ${VARIABLE_HEAD_CNAME_DECL}_${VARIABLE_HEAD_GUID_DECL}[${VARIABLE_HEAD_NUMSKUS_DECL}];
${END}
${BEGIN}  UINT16             StringTable${STRING_TABLE_INDEX}[${STRING_TABLE_LENGTH}]; /* ${STRING_TABLE_CNAME}_${STRING_TABLE_GUID} */
${END}
  SIZE_INFO          SizeTable[${PHASE}_SIZE_TABLE_SIZE];
${BEGIN}  UINT16             ${INIT_CNAME_DECL_UINT16}_${INIT_GUID_DECL_UINT16}[${INIT_NUMSKUS_DECL_UINT16}];
${END}
${BEGIN}  UINT16             ${VARDEF_CNAME_UINT16}_${VARDEF_GUID_UINT16}_VariableDefault_${VARDEF_SKUID_UINT16};
${END}
${BEGIN}  UINT8              ${INIT_CNAME_DECL_UINT8}_${INIT_GUID_DECL_UINT8}[${INIT_NUMSKUS_DECL_UINT8}];
${END}
${BEGIN}  UINT8              ${VARDEF_CNAME_UINT8}_${VARDEF_GUID_UINT8}_VariableDefault_${VARDEF_SKUID_UINT8};
${END}
${BEGIN}  BOOLEAN            ${INIT_CNAME_DECL_BOOLEAN}_${INIT_GUID_DECL_BOOLEAN}[${INIT_NUMSKUS_BOOLEAN}];
${END}
${BEGIN}  BOOLEAN            ${VARDEF_CNAME_BOOLEAN}_${VARDEF_GUID_BOOLEAN}_VariableDefault_${VARDEF_SKUID_BOOLEAN};
${END}
  UINT8              SkuIdTable[${PHASE}_SKUID_TABLE_SIZE];
${SYSTEM_SKU_ID}
} ${PHASE}_PCD_DATABASE_INIT;

typedef struct {
${PCD_DATABASE_UNINIT_EMPTY}
${BEGIN}  UINT64   ${UNINIT_CNAME_DECL_UINT64}_${UNINIT_GUID_DECL_UINT64}[${UNINIT_NUMSKUS_DECL_UINT64}];
${END}
${BEGIN}  UINT32   ${UNINIT_CNAME_DECL_UINT32}_${UNINIT_GUID_DECL_UINT32}[${UNINIT_NUMSKUS_DECL_UINT32}];
${END}
${BEGIN}  UINT16   ${UNINIT_CNAME_DECL_UINT16}_${UNINIT_GUID_DECL_UINT16}[${UNINIT_NUMSKUS_DECL_UINT16}];
${END}
${BEGIN}  UINT8    ${UNINIT_CNAME_DECL_UINT8}_${UNINIT_GUID_DECL_UINT8}[${UNINIT_NUMSKUS_DECL_UINT8}];
${END}
${BEGIN}  BOOLEAN  ${UNINIT_CNAME_DECL_BOOLEAN}_${UNINIT_GUID_DECL_BOOLEAN}[${UNINIT_NUMSKUS_DECL_BOOLEAN}];
${END}
} ${PHASE}_PCD_DATABASE_UNINIT;

#define PCD_${PHASE}_SERVICE_DRIVER_VERSION         2

typedef struct {
  ${PHASE}_PCD_DATABASE_INIT    Init;
  ${PHASE}_PCD_DATABASE_UNINIT  Uninit;
} ${PHASE}_PCD_DATABASE;

#define ${PHASE}_NEX_TOKEN_NUMBER (${PHASE}_LOCAL_TOKEN_NUMBER - ${PHASE}_EX_TOKEN_NUMBER)
"""

EmptyPcdDatabaseAutoGenC = """
${PHASE}_PCD_DATABASE_INIT g${PHASE}PcdDbInit = {
  /* ExMapTable */
  {
    {0, 0, 0}
  },
  /* LocalTokenNumberTable */
  {
    0
  },
  /* GuidTable */
  {
    {0x00000000, 0x0000, 0x0000, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}}
  },
  /* StringTable */
  { 0 },
  /* SizeTable */
  {
    0, 0
  },
  /* SkuIdTable */
  { 0 },
  ${SYSTEM_SKU_ID_VALUE}
};
"""

PcdDatabaseAutoGenC = """
${PHASE}_PCD_DATABASE_INIT g${PHASE}PcdDbInit = {
${BEGIN}  { ${INIT_VALUE_UINT64} }, /*  ${INIT_CNAME_DECL_UINT64}_${INIT_GUID_DECL_UINT64}[${INIT_NUMSKUS_DECL_UINT64}] */
${END}
${BEGIN}  ${VARDEF_VALUE_UINT64}, /* ${VARDEF_CNAME_UINT64}_${VARDEF_GUID_UINT64}_VariableDefault_${VARDEF_SKUID_UINT64} */
${END}
${BEGIN}  { ${INIT_VALUE_UINT32} }, /*  ${INIT_CNAME_DECL_UINT32}_${INIT_GUID_DECL_UINT32}[${INIT_NUMSKUS_DECL_UINT32}] */
${END}
${BEGIN}  ${VARDEF_VALUE_UINT32}, /* ${VARDEF_CNAME_UINT32}_${VARDEF_GUID_UINT32}_VariableDefault_${VARDEF_SKUID_UINT32} */
${END}
  /* VPD */
${BEGIN}  { ${VPD_HEAD_VALUE} }, /* ${VPD_HEAD_CNAME_DECL}_${VPD_HEAD_GUID_DECL}[${VPD_HEAD_NUMSKUS_DECL}] */
${END}
  /* ExMapTable */
  {
${BEGIN}    { ${EXMAPPING_TABLE_EXTOKEN}, ${EXMAPPING_TABLE_LOCAL_TOKEN}, ${EXMAPPING_TABLE_GUID_INDEX} },
${END}
  },
  /* LocalTokenNumberTable */
  {
${BEGIN}    offsetof(${PHASE}_PCD_DATABASE, ${TOKEN_INIT}.${TOKEN_CNAME}_${TOKEN_GUID}) | ${TOKEN_TYPE},
${END}
  },
  /* GuidTable */
  {
${BEGIN}    ${GUID_STRUCTURE},
${END}
  },
${BEGIN}  { ${STRING_HEAD_VALUE} }, /* ${STRING_HEAD_CNAME}_${STRING_HEAD_GUID}[${STRING_HEAD_NUMSKUS_DECL}] */
${END}
${BEGIN}  /* ${VARIABLE_HEAD_CNAME_DECL}_${VARIABLE_HEAD_GUID_DECL}[${VARIABLE_HEAD_NUMSKUS_DECL}] */
  {
    ${VARIABLE_HEAD_VALUE}
  },
${END}
 /* StringTable */
${BEGIN}  ${STRING_TABLE_VALUE}, /* ${STRING_TABLE_CNAME}_${STRING_TABLE_GUID} */
${END}
  /* SizeTable */
  {
${BEGIN}    ${SIZE_TABLE_CURRENT_LENGTH}, ${SIZE_TABLE_MAXIMUM_LENGTH}, /* ${SIZE_TABLE_CNAME}_${SIZE_TABLE_GUID} */
${END}
  },
${BEGIN}  { ${INIT_VALUE_UINT16} }, /*  ${INIT_CNAME_DECL_UINT16}_${INIT_GUID_DECL_UINT16}[${INIT_NUMSKUS_DECL_UINT16}] */
${END}
${BEGIN}  ${VARDEF_VALUE_UINT16}, /* ${VARDEF_CNAME_UINT16}_${VARDEF_GUID_UINT16}_VariableDefault_${VARDEF_SKUID_UINT16} */
${END}
${BEGIN}  { ${INIT_VALUE_UINT8} }, /*  ${INIT_CNAME_DECL_UINT8}_${INIT_GUID_DECL_UINT8}[${INIT_NUMSKUS_DECL_UINT8}] */
${END}
${BEGIN}  ${VARDEF_VALUE_UINT8}, /* ${VARDEF_CNAME_UINT8}_${VARDEF_GUID_UINT8}_VariableDefault_${VARDEF_SKUID_UINT8} */
${END}
${BEGIN}  { ${INIT_VALUE_BOOLEAN} }, /*  ${INIT_CNAME_DECL_BOOLEAN}_${INIT_GUID_DECL_BOOLEAN}[${INIT_NUMSKUS_DECL_BOOLEAN}] */
${END}
${BEGIN}  ${VARDEF_VALUE_BOOLEAN}, /* ${VARDEF_CNAME_BOOLEAN}_${VARDEF_GUID_BOOLEAN}_VariableDefault_${VARDEF_SKUID_BOOLEAN} */
${END}
  /* SkuIdTable */
  { ${BEGIN}${SKUID_VALUE}, ${END} },
${SYSTEM_SKU_ID_VALUE}
};
"""

#
# AutoGen File Header Templates
#
AutoGenHeaderString = """\
/**
  DO NOT EDIT
  FILE auto-generated
  Module name:
    $FileName
  Abstract:       Auto-generated $FileName for building module or library.
**/
"""

AutoGenHPrologueString = """
#ifndef _AUTOGENH_${Guid}
#define _AUTOGENH_${Guid}

extern int __make_me_compile_correctly;
"""

AutoGenHEpilogueString = """
#endif
"""

#
# PEI Core Entry Point Templates
#
PeiCoreEntryPointString = """
EFI_STATUS
${Function} (
  IN EFI_PEI_STARTUP_DESCRIPTOR  *PeiStartupDescriptor,
  IN VOID                        *OldCoreData
  );

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_PEI_STARTUP_DESCRIPTOR  *PeiStartupDescriptor,
  IN VOID                        *OldCoreData
  )

{
  return ${Function} (PeiStartupDescriptor, OldCoreData);
}
"""

#
# DXE Core Entry Point Templates
#
DxeCoreEntryPointString = """
const UINT32 _gUefiDriverRevision = 0;

VOID
${Function} (
  IN VOID  *HobStart
  );

VOID
EFIAPI
ProcessModuleEntryPointList (
  IN VOID  *HobStart
  )

{
  ${Function} (HobStart);
}
"""

#
# PEIM Entry Point Templates
#
PeimEntryPointString = [
"""
GLOBAL_REMOVE_IF_UNREFERENCED const UINT32 _gPeimRevision = 0;

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_FFS_FILE_HEADER  *FfsHeader,
  IN EFI_PEI_SERVICES     **PeiServices
  )

{
  return EFI_SUCCESS;
}
""",
"""
GLOBAL_REMOVE_IF_UNREFERENCED const UINT32 _gPeimRevision = 0;

EFI_STATUS
${Function} (
  IN EFI_FFS_FILE_HEADER  *FfsHeader,
  IN EFI_PEI_SERVICES     **PeiServices
  );

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_FFS_FILE_HEADER  *FfsHeader,
  IN EFI_PEI_SERVICES     **PeiServices
  )

{
  return ${Function} (FfsHeader, PeiServices);
}
""",
"""
GLOBAL_REMOVE_IF_UNREFERENCED const UINT32 _gPeimRevision = 0;

${BEGIN}
EFI_STATUS
${Function} (
  IN EFI_FFS_FILE_HEADER  *FfsHeader,
  IN EFI_PEI_SERVICES     **PeiServices
  );
${END}

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_FFS_FILE_HEADER  *FfsHeader,
  IN EFI_PEI_SERVICES     **PeiServices
  )

{
  EFI_STATUS  Status;
  EFI_STATUS  CombinedStatus;

  CombinedStatus = EFI_LOAD_ERROR;
${BEGIN}
  Status = ${Function} (FfsHeader, PeiServices);
  if (!EFI_ERROR (Status) || EFI_ERROR (CombinedStatus)) {
    CombinedStatus = Status;
  }
${END}
  return CombinedStatus;
}
"""
]

#
# DXE SMM Entry Point Templates
#
DxeSmmEntryPointString = [
"""
EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )

{
  return EFI_SUCCESS;
}
""",
"""
${BEGIN}
EFI_STATUS
${Function} (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  );
${END}

static BASE_LIBRARY_JUMP_BUFFER  mJumpContext;
static EFI_STATUS  mDriverEntryPointStatus = EFI_LOAD_ERROR;

VOID
EFIAPI
ExitDriver (
  IN EFI_STATUS  Status
  )
{
  if (!EFI_ERROR (Status) || EFI_ERROR (mDriverEntryPointStatus)) {
    mDriverEntryPointStatus = Status;
  }
  LongJump (&mJumpContext, (UINTN)-1);
  ASSERT (FALSE);
}

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )

{
${BEGIN}
  if (SetJump (&mJumpContext) == 0) {
    ExitDriver (${Function} (ImageHandle, SystemTable));
    ASSERT (FALSE);
  }
${END}

  return mDriverEntryPointStatus;
}
"""
]

#
# UEFI Entry Point Templates
#
UefiEntryPointString = [
"""
const UINT32 _gUefiDriverRevision = 0;

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  return EFI_SUCCESS;
}
""",
"""
const UINT32 _gUefiDriverRevision = 0;

EFI_STATUS
${Function} (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  );

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )

{
  return ${Function} (ImageHandle, SystemTable);
}

VOID
EFIAPI
ExitDriver (
  IN EFI_STATUS  Status
  )
{
  if (EFI_ERROR (Status)) {
    ProcessLibraryDestructorList (gImageHandle, gST);
  }
  gBS->Exit (gImageHandle, Status, 0, NULL);
}
""",
"""
const UINT32 _gUefiDriverRevision = 0;

${BEGIN}
EFI_STATUS
${Function} (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  );
${END}

EFI_STATUS
EFIAPI
ProcessModuleEntryPointList (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )

{
  ${BEGIN}
  if (SetJump (&mJumpContext) == 0) {
    ExitDriver (${Function} (ImageHandle, SystemTable));
    ASSERT (FALSE);
  }
  ${END}
  return mDriverEntryPointStatus;
}

static BASE_LIBRARY_JUMP_BUFFER  mJumpContext;
static EFI_STATUS  mDriverEntryPointStatus = EFI_LOAD_ERROR;

VOID
EFIAPI
ExitDriver (
  IN EFI_STATUS  Status
  )
{
  if (!EFI_ERROR (Status) || EFI_ERROR (mDriverEntryPointStatus)) {
    mDriverEntryPointStatus = Status;
  }
  LongJump (&mJumpContext, (UINTN)-1);
  ASSERT (FALSE);
}
"""
]

#
# UEFI Unload Image Templates
#
UefiUnloadImageString = [
"""
GLOBAL_REMOVE_IF_UNREFERENCED const UINT8 _gDriverUnloadImageCount = ${Count};

EFI_STATUS
EFIAPI
ProcessModuleUnloadList (
  IN EFI_HANDLE        ImageHandle
  )
{
  return EFI_SUCCESS;
}
""",
"""
GLOBAL_REMOVE_IF_UNREFERENCED const UINT8 _gDriverUnloadImageCount = ${Count};

${BEGIN}
EFI_STATUS
${Function} (
  IN EFI_HANDLE        ImageHandle
  );
${END}

EFI_STATUS
EFIAPI
ProcessModuleUnloadList (
  IN EFI_HANDLE        ImageHandle
  )
{
  return ${Function} (ImageHandle);
}
""",
"""
GLOBAL_REMOVE_IF_UNREFERENCED const UINT8 _gDriverUnloadImageCount = ${Count};

${BEGIN}
EFI_STATUS
${Function} (
  IN EFI_HANDLE        ImageHandle
  );
${END}

EFI_STATUS
EFIAPI
ProcessModuleUnloadList (
  IN EFI_HANDLE        ImageHandle
  )
{
  EFI_STATUS  Status;

  Status = EFI_SUCCESS;
${BEGIN}
  if (EFI_ERROR (Status)) {
    ${Function} (ImageHandle);
  } else {
    Status = ${Function} (ImageHandle);
  }
${END}
  return Status;
}
"""
]

#
# Library Constructor and Destructor Templates
#
LibraryString = [
"""
VOID
EFIAPI
ProcessLibrary${Type}List (
  VOID
  )
{
}
""",
"""
VOID
EFIAPI
ProcessLibrary${Type}List (
  IN EFI_FFS_FILE_HEADER       *FfsHeader,
  IN EFI_PEI_SERVICES          **PeiServices
  )
{
}
""",
"""
VOID
EFIAPI
ProcessLibrary${Type}List (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
}
""",
"""
${BEGIN}
RETURN_STATUS
EFIAPI
${Function} (
  VOID
  );
${END}

VOID
EFIAPI
ProcessLibrary${Type}List (
  VOID
  )
{
  EFI_STATUS  Status;

${BEGIN}
  Status = ${Function} ();
  ASSERT_EFI_ERROR (Status);
${END}
}
""",
"""
${BEGIN}
EFI_STATUS
EFIAPI
${Function} (
  IN EFI_FFS_FILE_HEADER       *FfsHeader,
  IN EFI_PEI_SERVICES          **PeiServices
  );
${END}

VOID
EFIAPI
ProcessLibrary${Type}List (
  IN EFI_FFS_FILE_HEADER       *FfsHeader,
  IN EFI_PEI_SERVICES          **PeiServices
  )
{
  EFI_STATUS  Status;

${BEGIN}
  Status = ${Function} (FfsHeader, PeiServices);
  ASSERT_EFI_ERROR (Status);
${END}
}
""",
"""
${BEGIN}
EFI_STATUS
EFIAPI
${Function} (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  );
${END}

VOID
EFIAPI
ProcessLibrary${Type}List (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  EFI_STATUS  Status;

${BEGIN}
  Status = ${Function} (ImageHandle, SystemTable);
  ASSERT_EFI_ERROR (Status);
${END}
}
"""
]

SpecificationString = """
${BEGIN}
#define ${Specification}
${END}
"""

BasicHeaderFile = "Base.h"

ModuleTypeHeaderFile = {
    "BASE"              :   BasicHeaderFile,
    "SEC"               :   "PiPei.h",
    "PEI_CORE"          :   "PiPei.h",
    "PEIM"              :   "PiPei.h",
    "DXE_CORE"          :   "PiDxe.h",
    "DXE_DRIVER"        :   "PiDxe.h",
    "DXE_SMM_DRIVER"    :   "PiDxe.h",
    "DXE_RUNTIME_DRIVER":   "PiDxe.h",
    "DXE_SAL_DRIVER"    :   "PiDxe.h",
    "UEFI_DRIVER"       :   "Uefi.h",
    "UEFI_APPLICATION"  :   "Uefi.h"
}

def GuidStringToGuidStructureString(Guid):
  GuidList = Guid.split('-')
  Result = '{'
  for Index in range(0,3,1):
    Result = Result + '0x' + GuidList[Index] + ', '
  Result = Result + '{0x' + GuidList[3][0:2] + ', 0x' + GuidList[3][2:4]
  for Index in range(0,12,2):
    Result = Result + ', 0x' + GuidList[4][Index:Index+2]
  Result += '}}'
  return Result

def GuidStructureStringToGuidString(GuidValue):
    guidValueString = GuidValue.lower().replace("{", "").replace("}", "").replace(" ", "")
    guidValueList = guidValueString.split(",")
    if len(guidValueList) != 11:
        EdkLogger.error("Invalid GUID value string %s" % GuidValue)
        return None
    return "%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x" % (
            int(guidValueList[0], 16),
            int(guidValueList[1], 16),
            int(guidValueList[2], 16),
            int(guidValueList[3], 16),
            int(guidValueList[4], 16),
            int(guidValueList[5], 16),
            int(guidValueList[6], 16),
            int(guidValueList[7], 16),
            int(guidValueList[8], 16),
            int(guidValueList[9], 16),
            int(guidValueList[10], 16)
            )

class AutoGenString(object):
  def __init__(self):
    self.String = ''

  def Append(self, AppendString, Dictionary=None):
    if Dictionary == None:
      self.String += AppendString
    else:
      while AppendString.find('${BEGIN}') >= 0:
        Start = AppendString.find('${BEGIN}')
        End   = AppendString.find('${END}')
        SubString = AppendString[AppendString.find('${BEGIN}'):AppendString.find('${END}')+6]
        Max = 0
        MaxLen = {}
        for Key in Dictionary:
          if SubString.find('$'+Key) >= 0 or SubString.find('${'+Key+'}') >= 0:
            Value = Dictionary[Key]
            if type(Value) == type([]):
              MaxLen[Key] = len(Value)
            else:
              MaxLen[Key] = 1
            if MaxLen[Key] > Max:
              Max = MaxLen[Key]

        NewString = ''
        for Index in range(0,Max):
          NewDict = {'BEGIN':'','END':''}
          for Key in MaxLen:
            NewDict[Key] = Dictionary[Key]
            if type(Dictionary[Key]) == type([]):
              NewDict[Key] = Dictionary[Key][Index]
          NewString += string.Template(SubString).safe_substitute(NewDict)
        AppendString = AppendString[0:Start] + NewString + AppendString[End+6:]
      NewDict = {}
      for Key in Dictionary:
        NewDict[Key] = Dictionary[Key]
        if type(Dictionary[Key]) == type([]) and len(Dictionary[Key]) > 0:
          NewDict[Key] = Dictionary[Key][0]
      self.String += string.Template(AppendString).safe_substitute(NewDict)
