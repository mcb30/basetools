/** @file

Copyright (c) 2004 - 2008, Intel Corporation                                                         
All rights reserved. This program and the accompanying materials                          
are licensed and made available under the terms and conditions of the BSD License         
which accompanies this distribution.  The full text of the license may be found at        
http://opensource.org/licenses/bsd-license.php                                            
                                                                                          
THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,                     
WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.             

Module Name:
  
  GenFvInternalLib.h

Abstract:

  This file contains describes the public interfaces to the GenFvImage Library.
  The basic purpose of the library is to create Firmware Volume images.

**/

#ifndef _EFI_GEN_FV_INTERNAL_LIB_H
#define _EFI_GEN_FV_INTERNAL_LIB_H

//
// Include files
//
#include <stdlib.h>

#include <Common/UefiBaseTypes.h>
#include <Common/UefiCapsule.h>

#include <Common/PiFirmwareFile.h>
#include <Common/PiFirmwareVolume.h>
#include <Guid/PiFirmwareFileSystem.h>
#include <IndustryStandard/PeImage.h>

#include "CommonLib.h"
#include "ParseInf.h"
#include "EfiUtilityMsgs.h"

extern UINT32 mFvTotalSize;
extern UINT32 mFvTakenSize;
//
// Different file separater for Linux and Windows
//
#define FILE_SEP_CHAR '/'

//
// The maximum number of Pad file guid entries.
//
#define MAX_NUMBER_OF_PAD_FILE_GUIDS    1024

//
// The maximum number of block map entries supported by the library
//
#define MAX_NUMBER_OF_FV_BLOCKS         100

//
// The maximum number of files in the FV supported by the library
//
#define MAX_NUMBER_OF_FILES_IN_FV       1000
#define MAX_NUMBER_OF_FILES_IN_CAP      1000
#define EFI_FFS_FILE_HEADER_ALIGNMENT   8

//
// INF file strings
//
#define OPTIONS_SECTION_STRING            "[options]"
#define ATTRIBUTES_SECTION_STRING         "[attributes]"
#define FILES_SECTION_STRING              "[files]"

//
// Options section
//
#define EFI_FV_BASE_ADDRESS_STRING        "EFI_BASE_ADDRESS"
#define EFI_FV_FILE_NAME_STRING           "EFI_FILE_NAME"
#define EFI_NUM_BLOCKS_STRING             "EFI_NUM_BLOCKS"
#define EFI_BLOCK_SIZE_STRING             "EFI_BLOCK_SIZE"
#define EFI_FV_GUID_STRING                "EFI_FV_GUID"
#define EFI_CAPSULE_GUID_STRING           "EFI_CAPSULE_GUID"
#define EFI_CAPSULE_HEADER_SIZE_STRING    "EFI_CAPSULE_HEADER_SIZE"
#define EFI_CAPSULE_FLAGS_STRING          "EFI_CAPSULE_FLAGS"
#define EFI_CAPSULE_VERSION_STRING        "EFI_CAPSULE_VERSION"
#define EFI_FV_BOOT_DRIVER_BASE_ADDRESS_STRING    "EFI_BOOT_DRIVER_BASE_ADDRESS"
#define EFI_FV_RUNTIME_DRIVER_BASE_ADDRESS_STRING "EFI_RUNTIME_DRIVER_BASE_ADDRESS"

#define EFI_FV_TOTAL_SIZE_STRING    "EFI_FV_TOTAL_SIZE"
#define EFI_FV_TAKEN_SIZE_STRING    "EFI_FV_TAKEN_SIZE"
#define EFI_FV_SPACE_SIZE_STRING    "EFI_FV_SPACE_SIZE"

//
// Attributes section
//
#define EFI_FVB2_READ_DISABLED_CAP_STRING  "EFI_READ_DISABLED_CAP"
#define EFI_FVB2_READ_ENABLED_CAP_STRING   "EFI_READ_ENABLED_CAP"
#define EFI_FVB2_READ_STATUS_STRING        "EFI_READ_STATUS"

#define EFI_FVB2_WRITE_DISABLED_CAP_STRING "EFI_WRITE_DISABLED_CAP"
#define EFI_FVB2_WRITE_ENABLED_CAP_STRING  "EFI_WRITE_ENABLED_CAP"
#define EFI_FVB2_WRITE_STATUS_STRING       "EFI_WRITE_STATUS"

#define EFI_FVB2_LOCK_CAP_STRING           "EFI_LOCK_CAP"
#define EFI_FVB2_LOCK_STATUS_STRING        "EFI_LOCK_STATUS"

#define EFI_FVB2_STICKY_WRITE_STRING       "EFI_STICKY_WRITE"
#define EFI_FVB2_MEMORY_MAPPED_STRING      "EFI_MEMORY_MAPPED"
#define EFI_FVB2_ERASE_POLARITY_STRING     "EFI_ERASE_POLARITY"

#define EFI_FVB2_READ_LOCK_CAP_STRING      "EFI_READ_LOCK_CAP"
#define EFI_FVB2_READ_LOCK_STATUS_STRING   "EFI_READ_LOCK_STATUS"
#define EFI_FVB2_WRITE_LOCK_CAP_STRING     "EFI_WRITE_LOCK_CAP"
#define EFI_FVB2_WRITE_LOCK_STATUS_STRING  "EFI_WRITE_LOCK_STATUS"

#define EFI_FVB2_ALIGNMENT_1_STRING       "EFI_FVB2_ALIGNMENT_1"   
#define EFI_FVB2_ALIGNMENT_2_STRING       "EFI_FVB2_ALIGNMENT_2"   
#define EFI_FVB2_ALIGNMENT_4_STRING       "EFI_FVB2_ALIGNMENT_4"   
#define EFI_FVB2_ALIGNMENT_8_STRING       "EFI_FVB2_ALIGNMENT_8"   
#define EFI_FVB2_ALIGNMENT_16_STRING      "EFI_FVB2_ALIGNMENT_16"  
#define EFI_FVB2_ALIGNMENT_32_STRING      "EFI_FVB2_ALIGNMENT_32"  
#define EFI_FVB2_ALIGNMENT_64_STRING      "EFI_FVB2_ALIGNMENT_64"  
#define EFI_FVB2_ALIGNMENT_128_STRING     "EFI_FVB2_ALIGNMENT_128" 
#define EFI_FVB2_ALIGNMENT_256_STRING     "EFI_FVB2_ALIGNMENT_256" 
#define EFI_FVB2_ALIGNMENT_512_STRING     "EFI_FVB2_ALIGNMENT_512" 
#define EFI_FVB2_ALIGNMENT_1K_STRING      "EFI_FVB2_ALIGNMENT_1K"  
#define EFI_FVB2_ALIGNMENT_2K_STRING      "EFI_FVB2_ALIGNMENT_2K"  
#define EFI_FVB2_ALIGNMENT_4K_STRING      "EFI_FVB2_ALIGNMENT_4K"  
#define EFI_FVB2_ALIGNMENT_8K_STRING      "EFI_FVB2_ALIGNMENT_8K"  
#define EFI_FVB2_ALIGNMENT_16K_STRING     "EFI_FVB2_ALIGNMENT_16K" 
#define EFI_FVB2_ALIGNMENT_32K_STRING     "EFI_FVB2_ALIGNMENT_32K" 
#define EFI_FVB2_ALIGNMENT_64K_STRING     "EFI_FVB2_ALIGNMENT_64K" 
#define EFI_FVB2_ALIGNMENT_128K_STRING    "EFI_FVB2_ALIGNMENT_128K"
#define EFI_FVB2_ALIGNMENT_256K_STRING    "EFI_FVB2_ALIGNMENT_256K"
#define EFI_FVB2_ALIGNMNET_512K_STRING    "EFI_FVB2_ALIGNMENT_512K"
#define EFI_FVB2_ALIGNMENT_1M_STRING      "EFI_FVB2_ALIGNMENT_1M"  
#define EFI_FVB2_ALIGNMENT_2M_STRING      "EFI_FVB2_ALIGNMENT_2M"  
#define EFI_FVB2_ALIGNMENT_4M_STRING      "EFI_FVB2_ALIGNMENT_4M"  
#define EFI_FVB2_ALIGNMENT_8M_STRING      "EFI_FVB2_ALIGNMENT_8M"  
#define EFI_FVB2_ALIGNMENT_16M_STRING     "EFI_FVB2_ALIGNMENT_16M" 
#define EFI_FVB2_ALIGNMENT_32M_STRING     "EFI_FVB2_ALIGNMENT_32M" 
#define EFI_FVB2_ALIGNMENT_64M_STRING     "EFI_FVB2_ALIGNMENT_64M" 
#define EFI_FVB2_ALIGNMENT_128M_STRING    "EFI_FVB2_ALIGNMENT_128M"
#define EFI_FVB2_ALIGNMENT_256M_STRING    "EFI_FVB2_ALIGNMENT_256M"
#define EFI_FVB2_ALIGNMENT_512M_STRING    "EFI_FVB2_ALIGNMENT_512M"
#define EFI_FVB2_ALIGNMENT_1G_STRING      "EFI_FVB2_ALIGNMENT_1G"  
#define EFI_FVB2_ALIGNMENT_2G_STRING      "EFI_FVB2_ALIGNMENT_2G"  

//
// File sections
//
#define EFI_FILE_NAME_STRING      "EFI_FILE_NAME"

#define ONE_STRING                "1"
#define ZERO_STRING               "0"
#define TRUE_STRING               "TRUE"
#define FALSE_STRING              "FALSE"
#define NULL_STRING               "NULL"

//
// Defines to calculate the offset for PEI CORE entry points
//
#define IA32_PEI_CORE_ENTRY_OFFSET    0x20

//
// Defines to calculate the offset for IA32 SEC CORE entry point
//
#define IA32_SEC_CORE_ENTRY_OFFSET     0xD

//
// Defines to calculate the FIT table
//
#define IPF_FIT_ADDRESS_OFFSET        0x20

//
// Defines to calculate the offset for SALE_ENTRY
//
#define IPF_SALE_ENTRY_ADDRESS_OFFSET 0x18

//
// Symbol file definitions, current max size if 512K
//
#define SYMBOL_FILE_SIZE              0x80000

#define FV_IMAGES_TOP_ADDRESS         0x100000000ULL

//
// Following definition is used for FIT in IPF
//
#define COMP_TYPE_FIT_PEICORE 0x10
#define COMP_TYPE_FIT_UNUSED  0x7F

#define FIT_TYPE_MASK         0x7F
#define CHECKSUM_BIT_MASK     0x80

//
// Rebase File type
//
#define REBASE_XIP_FILE       0x1
#define REBASE_BOOTTIME_FILE  0x2
#define REBASE_RUNTIME_FILE   0x4

//
// Private data types
//
//
// Component information
//
typedef struct {
  UINTN Size;
  CHAR8 ComponentName[_MAX_PATH];
} COMPONENT_INFO;

//
// FV and capsule information holder
//
typedef struct {
  EFI_PHYSICAL_ADDRESS    BaseAddress;
  EFI_PHYSICAL_ADDRESS    BootBaseAddress;
  EFI_PHYSICAL_ADDRESS    RuntimeBaseAddress;  
  EFI_GUID                FvGuid;
  UINTN                   Size;
  CHAR8                   FvName[_MAX_PATH];
  EFI_FV_BLOCK_MAP_ENTRY  FvBlocks[MAX_NUMBER_OF_FV_BLOCKS];
  EFI_FVB_ATTRIBUTES      FvAttributes;
  CHAR8                   FvFiles[MAX_NUMBER_OF_FILES_IN_FV][_MAX_PATH];
} FV_INFO;

typedef struct {
  EFI_GUID                CapGuid;
  UINT32                  HeaderSize;
  UINT32                  Flags;
  CHAR8                   CapName[_MAX_PATH];
  CHAR8                   CapFiles[MAX_NUMBER_OF_FILES_IN_CAP][_MAX_PATH];
} CAP_INFO;

#pragma pack(1)

typedef struct {
  UINT64  CompAddress;
  UINT32  CompSize;
  UINT16  CompVersion;
  UINT8   CvAndType;
  UINT8   CheckSum;
} FIT_TABLE;

#pragma pack()

#define FV_DEFAULT_ATTRIBUTE  0x0004FEFF
extern FV_INFO    gFvDataInfo;
extern CAP_INFO   gCapDataInfo;
//
// Local function prototypes
//
EFI_STATUS
ParseFvInf (
  IN  MEMORY_FILE  *InfFile,
  OUT FV_INFO      *FvInfo
  )
;

EFI_STATUS
UpdatePeiCoreEntryInFit (
  IN FIT_TABLE     *FitTablePtr,
  IN UINT64        PeiCorePhysicalAddress
  )
/*++

Routine Description:

  This function is used to update the Pei Core address in FIT, this can be used by Sec core to pass control from
  Sec to Pei Core

Arguments:

  FitTablePtr             - The pointer of FIT_TABLE.
  PeiCorePhysicalAddress  - The address of Pei Core entry.

Returns:

  EFI_SUCCESS             - The PEI_CORE FIT entry was updated successfully.
  EFI_NOT_FOUND           - Not found the PEI_CORE FIT entry.

--*/
;

VOID
UpdateFitCheckSum (
  IN FIT_TABLE   *FitTablePtr
  )
/*++

Routine Description:

  This function is used to update the checksum for FIT.


Arguments:

  FitTablePtr             - The pointer of FIT_TABLE.

Returns:

  None.

--*/
;

EFI_STATUS
GetPe32Info (
  IN UINT8                  *Pe32,
  OUT UINT32                *EntryPoint,
  OUT UINT32                *BaseOfCode,
  OUT UINT16                *MachineType
  );

EFI_STATUS
ParseCapInf (
  IN  MEMORY_FILE  *InfFile,
  OUT CAP_INFO     *CapInfo
  );

EFI_STATUS
FindApResetVectorPosition (
  IN  MEMORY_FILE  *FvImage,
  OUT UINT8        **Pointer
  ); 

EFI_STATUS
CalculateFvSize (
  FV_INFO *FvInfoPtr
  );

EFI_STATUS
FfsRebase ( 
  IN OUT  FV_INFO               *FvInfo, 
  IN      CHAR8                 *FileName,           
  IN OUT  EFI_FFS_FILE_HEADER   *FfsFile,
  IN      UINTN                 XipOffset,
  IN      FILE                  *FvMapFile
  );

//
// Exported function prototypes
//
EFI_STATUS
GenerateCapImage (
  IN CHAR8                *InfFileImage,
  IN UINTN                InfFileSize,
  IN CHAR8                *CapFileName
  )
/*++

Routine Description:

  This is the main function which will be called from application to 
  generate UEFI Capsule image.

Arguments:

  InfFileImage   Buffer containing the INF file contents.
  InfFileSize    Size of the contents of the InfFileImage buffer.
  CapFileName    Requested name for the Cap file.

Returns:

  EFI_SUCCESS             Function completed successfully.
  EFI_OUT_OF_RESOURCES    Could not allocate required resources.
  EFI_ABORTED             Error encountered.
  EFI_INVALID_PARAMETER   A required parameter was NULL.

--*/
;

EFI_STATUS
GenerateFvImage (
  IN CHAR8                *InfFileImage,
  IN UINTN                InfFileSize,
  IN CHAR8                *FvFileName,  
  IN CHAR8                *MapFileName,
  IN EFI_PHYSICAL_ADDRESS XipBaseAddress,
  IN EFI_PHYSICAL_ADDRESS *BtBaseAddress,
  IN EFI_PHYSICAL_ADDRESS *RtBaseAddress
  )
/*++

Routine Description:

  This is the main function which will be called from application to 
  generate Firmware Image conforms to PI spec.

Arguments:

  InfFileImage   Buffer containing the INF file contents.
  InfFileSize    Size of the contents of the InfFileImage buffer.
  FvFileName     Requested name for the FV file.
  MapFileName    Fv map file to log fv driver information.
  XipBaseAddress BaseAddress is to be rebased.
  BtBaseAddress  Pointer to BaseAddress is to set the prefer loaded image start address for boot drivers.
  RtBaseAddress  Pointer to BaseAddress is to set the prefer loaded image start address for runtime drivers.
    
Returns:
 
  EFI_SUCCESS             Function completed successfully.
  EFI_OUT_OF_RESOURCES    Could not allocate required resources.
  EFI_ABORTED             Error encountered.
  EFI_INVALID_PARAMETER   A required parameter was NULL.

--*/
;

EFI_STATUS
WriteMapFile (
  IN OUT FILE                  *FvMapFile,
  IN     CHAR8                 *FileName,
  IN     EFI_GUID              *FileGuidPtr, 
  IN     EFI_PHYSICAL_ADDRESS  ImageBaseAddress,
  IN     UINT32                AddressOfEntryPoint,
  IN     UINT32                Offset
  );
#endif
