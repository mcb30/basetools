/*++

Copyright (c)  1999 - 2006, Intel Corporation. All rights reserved
This software and associated documentation (if any) is furnished
under a license and may only be used or copied in accordance
with the terms of the license. Except as permitted by such
license, no part of this software or documentation may be
reproduced, stored in a retrieval system, or transmitted in any
form or by any means without the express written consent of
Intel Corporation.


Module Name:

  GenVtf.c

Abstract:

  This file contains functions required to generate a boot strap file (VTF) 
  also known as the Volume Top File (VTF)

--*/

//
// Module Coded to EFI 2.0 Coding Conventions
//
#include <FvLib.h>
#include <Common/UefiBaseTypes.h>
#include "GenVtf.h"
#include <Guid/PiFirmwareFileSystem.h>
#include "CommonLib.h"

//
// Global variables
//
EFI_GUID      Vtf1NameGuid = EFI_IPF_VTF1_GUID
EFI_GUID      Vtf2NameGuid = EFI_IPF_VTF2_GUID

//CHAR8       OutFileName1[FILE_NAME_SIZE];
//CHAR8       OutFileName2[FILE_NAME_SIZE];

BOOLEAN     VTF_OUTPUT = FALSE;
CHAR8       *OutFileName1;
CHAR8       *OutFileName2;

CHAR8           **TokenStr;
CHAR8           **OrgStrTokPtr;

PARSED_VTF_INFO *FileListPtr;
PARSED_VTF_INFO *FileListHeadPtr;

VOID            *Vtf1Buffer;
VOID            *Vtf1EndBuffer;
VOID            *Vtf2Buffer;
VOID            *Vtf2EndBuffer;

UINTN           ValidLineNum        = 0;
UINTN           ValidFFDFileListNum = 0;

//
// Section Description and their number of occurences in *.INF file
//
UINTN           NumFvFiles        = 0;
UINTN           SectionOptionNum  = 0;

//
// Global flag which will check for VTF Present, if yes then will be used
// to decide about adding FFS header to pad data
//
BOOLEAN         VTFPresent = FALSE;
BOOLEAN         SecondVTF = FALSE;
//
// Address related information
//
UINT64          Fv1BaseAddress        = 0;
UINT64          Fv2BaseAddress        = 0;
UINT64          Fv1EndAddress         = 0;
UINT64          Fv2EndAddress         = 0;
UINT32          Vtf1TotalSize         = SIZE_TO_OFFSET_PAL_A_END;
UINT64          Vtf1LastStartAddress  = 0;
UINT32          Vtf2TotalSize         = 0;
UINT64          Vtf2LastStartAddress  = 0;

UINT32          BufferToTop           = 0;

//
// IA32 Reset Vector Bin name
//
CHAR8           IA32BinFile[FILE_NAME_SIZE];
  
//
// Function Implementations
//
VOID
BuildTokenList (
  IN  CHAR8 *Token
  )
/*++
Routine Description:

  This function builds the token list in an array which will be parsed later

Arguments:

  Token    - The pointer of string

Returns:

  None

--*/
{
  strcpy (*TokenStr, Token);
//  fprintf(stdout,*TokenStr);
//  printf("\n");
  TokenStr++;
}

EFI_STATUS
ConvertVersionInfo (
  IN      CHAR8     *Str,
  IN OUT  UINT8     *MajorVer,
  IN OUT  UINT8     *MinorVer
  )
/*++
Routine Description:

  This function converts GUID string to GUID

Arguments:

  Str      - String representing in form XX.XX
  MajorVer - The major vertion
  MinorVer - The minor vertion

Returns:

  EFI_SUCCESS  - The fuction completed successfully.

--*/
{
  CHAR8 StrPtr[40];
  CHAR8 *Token;
  UINTN Length;
  UINTN Major;
  UINTN Minor;

  Major = 0;
  Minor = 0;
  memset (StrPtr, 0, 40);
  Token = strtok (Str, ".");

  while (Token != NULL) {
    strcat (StrPtr, Token);
    Token = strtok (NULL, ".");
  }

  Length = strlen (StrPtr);
  sscanf (
    StrPtr,
    "%01x%02x",
    &Major,
    &Minor
    );

  *MajorVer = (UINT8) Major;
  *MinorVer = (UINT8) Minor;
  return EFI_SUCCESS;
}

VOID
TrimLine (
  IN  CHAR8 *Line
  )
/*++
Routine Description:

  This function cleans up the line by removing all whitespace and 
  comments

Arguments:

  Line   - The pointer of the string

Returns:

  None

--*/
{
  CHAR8 TmpLine[FILE_NAME_SIZE];
  CHAR8 Char;
  CHAR8 *Ptr0;
  UINTN Index;
  UINTN Index2;

  //
  // Change '#' to '//' for Comment style
  //
  if (((Ptr0 = strchr (Line, '#')) != NULL) || ((Ptr0 = strstr (Line, "//")) != NULL)) {
    Line[Ptr0 - Line] = 0;
  }

  //
  // Initialize counters
  //
  Index   = 0;
  Index2  = 0;

  while ((Char = Line[Index]) != 0) {
    if ((Char != ' ') && (Char != '\t') && (Char != '\n')) {
      TmpLine[Index2++] = Char;
    }
    Index++;
  }

  TmpLine[Index2] = 0;
  strcpy (Line, TmpLine);
}

VOID
ValidLineCount (
  IN  FILE *Fp
  )
/*++

Routine Description:

  This function calculated number of valid lines in a input file.
  
Arguments:

  Fp    - Pointer to a file handle which has been opened.

Returns:

  None

--*/
{
  CHAR8 Buff[FILE_NAME_SIZE];
  while (fgets(Buff, sizeof (Buff), Fp)) {
    TrimLine (Buff);
    if (Buff[0] == 0) {
      continue;
    }
    ValidLineNum++;
  }
//  printf("\n%d", ValidLineNum);
}

VOID
ParseInputFile (
  IN  FILE *Fp
  )
/*++
  
Routine Description:

  This function parses the input file and tokenize the string
  
Arguments:

  Fp    - Pointer to a file handle which has been opened.
  
Returns:

  None

--*/
{
  CHAR8 *Token;
  CHAR8 Buff[FILE_NAME_SIZE];
  CHAR8 OrgLine[FILE_NAME_SIZE];
  CHAR8 Str[FILE_NAME_SIZE];
  CHAR8 Delimit[] = "=";

  while (fgets (Buff, sizeof (Buff), Fp) != NULL) {
    strcpy (OrgLine, Buff);
    TrimLine (Buff);
    if (Buff[0] == 0) {
      continue;
    }
    Token = strtok (Buff, Delimit);

    while (Token != NULL) {
      strcpy (Str, Token);
      BuildTokenList (Str);
      Token = strtok (NULL, Delimit);
    }
  }
}

EFI_STATUS
InitializeComps (
  VOID
  )
/*++

Routine Description:

  This function intializes the relevant global variable which is being
  used to store the information retrieved from INF file.  This also initializes
  the VTF symbol file.
  
Arguments:

  None

Returns:

  EFI_SUCCESS            - The function completed successfully
  EFI_OUT_OF_RESOURCES   - Malloc failed.

--*/
{

  FileListPtr = malloc (sizeof (PARSED_VTF_INFO));

  if (FileListPtr == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }

  FileListHeadPtr = FileListPtr;
  memset (FileListPtr, 0, sizeof (PARSED_VTF_INFO));
  FileListPtr->NextVtfInfo = NULL;

  remove (VTF_SYM_FILE);
  return EFI_SUCCESS;
}

VOID
ParseAndUpdateComponents (
  IN  PARSED_VTF_INFO   *VtfInfo
  )
/*++

Routine Description:

  This function intializes the relevant global variable which is being
  used to store the information retrieved from INF file.
  
Arguments:

  VtfInfo  - A pointer to the VTF Info Structure
  

Returns:

  None

--*/
{
  UINT64  StringValue;

  while (*TokenStr != NULL && (strnicmp (*TokenStr, "COMP_NAME", 9) != 0)) {

    if (strnicmp (*TokenStr, "COMP_LOC", 8) == 0) {
      TokenStr++;
      if (strnicmp (*TokenStr, "F", 1) == 0) {
        VtfInfo->LocationType = FIRST_VTF;
      } else if (strnicmp (*TokenStr, "S", 1) == 0) {
        VtfInfo->LocationType = SECOND_VTF;
      } else {
        VtfInfo->LocationType = NONE;
//        printf ("\nERROR: Unknown location for component %s", VtfInfo->CompName);
      }
    } else if (strnicmp (*TokenStr, "COMP_TYPE", 9) == 0) {
      TokenStr++;
      if (AsciiStringToUint64 (*TokenStr, FALSE, &StringValue) != EFI_SUCCESS) {
//        printf ("\nERROR: Could not read a numeric value from \"%s\".", TokenStr);
        return ;
      }

      VtfInfo->CompType = (UINT8) StringValue;
    } else if (strnicmp (*TokenStr, "COMP_VER", 8) == 0) {
      TokenStr++;
      if (strnicmp (*TokenStr, "-", 1) == 0) {
        VtfInfo->VersionPresent = FALSE;
        VtfInfo->MajorVer       = 0;
        VtfInfo->MinorVer       = 0;
      } else {
        VtfInfo->VersionPresent = TRUE;
        ConvertVersionInfo (*TokenStr, &VtfInfo->MajorVer, &VtfInfo->MinorVer);
      }
    } else if (strnicmp (*TokenStr, "COMP_BIN", 8) == 0) {
      TokenStr++;
      strcpy (VtfInfo->CompBinName, *TokenStr);
    } else if (strnicmp (*TokenStr, "COMP_SYM", 8) == 0) {
      TokenStr++;
      strcpy (VtfInfo->CompSymName, *TokenStr);
    } else if (strnicmp (*TokenStr, "COMP_SIZE", 9) == 0) {
      TokenStr++;
      if (strnicmp (*TokenStr, "-", 1) == 0) {
        VtfInfo->PreferredSize  = FALSE;
        VtfInfo->CompSize       = 0;
      } else {
        VtfInfo->PreferredSize = TRUE;
        if (AsciiStringToUint64 (*TokenStr, FALSE, &StringValue) != EFI_SUCCESS) {
          printf ("\nERROR: Could not read a numeric value from \"%s\".", TokenStr);
          return ;
        }

        VtfInfo->CompSize = (UINTN) StringValue;
      }

    } else if (strnicmp (*TokenStr, "COMP_CS", 7) == 0) {
      TokenStr++;
      if (strnicmp (*TokenStr, "1", 1) == 0) {
        VtfInfo->CheckSumRequired = 1;
      } else if (strnicmp (*TokenStr, "0", 1) == 0) {
        VtfInfo->CheckSumRequired = 0;
      } else {
        printf ("\nERROR: Bad information in INF file about Checksum required field");
      }
    }

    TokenStr++;
    if (*TokenStr == NULL) {
      break;
    }
  }
}

VOID
InitializeInFileInfo (
  VOID
  )
/*++

Routine Description:

  This function intializes the relevant global variable which is being
  used to store the information retrieved from INF file.

Arguments:

  NONE

Returns:

  NONE

--*/
{
  UINTN SectionOptionFlag;
  UINTN SectionCompFlag;

  SectionOptionFlag = 0;
  SectionCompFlag   = 0;
  TokenStr          = OrgStrTokPtr;
  while (*TokenStr != NULL) {
//    fprintf(stdout, *TokenStr);
//    printf("\n");
//    printf("\nTokenStr is %c", **TokenStr);
    if (strnicmp (*TokenStr, "[OPTIONS]", 9) == 0) {
//      printf("\n Parse [OPTIONS] start!");
      SectionOptionFlag = 1;
      SectionCompFlag   = 0;
    }

    if (strnicmp (*TokenStr, "[COMPONENTS]", 12) == 0) {
//      printf("\n Parse [COMPONENTS] start!");
      if (FileListPtr == NULL) {
        FileListPtr = FileListHeadPtr;
      }

      SectionCompFlag   = 1;
      SectionOptionFlag = 0;
      TokenStr++;
    }

    if (SectionOptionFlag) {
      if (stricmp (*TokenStr, "IA32_RST_BIN") == 0) {
//        printf("\n Parse IA32_RST_BIN start!");
        *TokenStr++;
        strcpy (IA32BinFile, *TokenStr);
      }
    }

    if (SectionCompFlag) {
      if (stricmp (*TokenStr, "COMP_NAME") == 0) {
//        printf("\n Parse COMP_NAME start!");
        TokenStr++;
        strcpy (FileListPtr->CompName, *TokenStr);
        TokenStr++;
//        printf("\nStart to call ParseAndUpdateComponents!");
        ParseAndUpdateComponents (FileListPtr);
      }

      if (*TokenStr != NULL) {
        FileListPtr->NextVtfInfo  = malloc (sizeof (PARSED_VTF_INFO));
        if (FileListPtr->NextVtfInfo == NULL) {
          printf ("Error: Out of memory resources.\n");
          break;
        }
        FileListPtr = FileListPtr->NextVtfInfo;
        memset (FileListPtr, 0, sizeof (PARSED_VTF_INFO));
        FileListPtr->NextVtfInfo = NULL;
        continue;
      } else {
        break;
      }
    }

    TokenStr++;
  }
//  printf("\nWe are done here, InitializeInFileInfo!");
}

EFI_STATUS
GetVtfRelatedInfoFromInfFile (
//  IN  CHAR8 *FileName
  IN FILE *FilePointer
  )
/*++
  
Routine Description:

  This function reads the input file, parse it and create a list of tokens
  which is parsed and used, to intialize the data related to VTF
  
Arguments:

  FileName  - FileName which needed to be read to parse data

Returns:
   
  EFI_ABORTED           - Error in opening file
  EFI_INVALID_PARAMETER - File doesn't contain any valid informations
  EFI_OUT_OF_RESOURCES  - Malloc Failed
  EFI_SUCCESS           - The function completed successfully 

--*/
{
  FILE        *Fp;
  UINTN       Index;
  EFI_STATUS  Status;
  
//  Fp = fopen (FileName, "r");
  Fp = FilePointer;
  if (Fp == NULL) {
//    printf ("\nERROR: Error in opening %s file\n", FileName);
    printf("\nERROR: BSF INF file is invalid!\n");
    return EFI_ABORTED;
  }

//  printf("\nStart to call ValidLineCount");
  ValidLineCount (Fp);

  if (ValidLineNum == 0) {
    printf ("\nERROR: File doesn't contain any valid informations");
    return EFI_INVALID_PARAMETER;
  }

  TokenStr = (CHAR8 **) malloc (sizeof (UINTN) * (2 * ValidLineNum + 1));

  if (TokenStr == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }

  memset (TokenStr, 0, (sizeof (UINTN) * (2 * ValidLineNum + 1)));
  OrgStrTokPtr = TokenStr;

  for (Index = 0; Index < (2 * ValidLineNum); Index++) {
    *TokenStr = (CHAR8*)malloc (sizeof (CHAR8) * FILE_NAME_SIZE);

    if (*TokenStr == NULL) {
      free (OrgStrTokPtr);
      return EFI_OUT_OF_RESOURCES;
    }

    memset (*TokenStr, 0, FILE_NAME_SIZE);
//    free (*TokenStr);
    TokenStr++;
  }

  TokenStr  = NULL;
  TokenStr  = OrgStrTokPtr;
  fseek (Fp, 0L, SEEK_SET);
 
  Status = InitializeComps ();

  if (Status != EFI_SUCCESS) {
    free (OrgStrTokPtr);
    return Status;
  }
  
  ParseInputFile (Fp);
  
//  printf("\nStart to call InitializeInFileInfo!");
  InitializeInFileInfo ();

  if (Fp) {
    fclose (Fp);
  }
  free (OrgStrTokPtr);
  return EFI_SUCCESS;
}

VOID
GetRelativeAddressInVtfBuffer (
  IN      UINT64     Address,
  IN OUT  UINTN      *RelativeAddress,
  IN      LOC_TYPE   LocType
  )
/*++
  
Routine Description:

  This function checks for the address alignmnet for specified data boundary. In
  case the address is not aligned, it returns FALSE and the amount of data in 
  terms of byte needed to adjust to get the boundary alignmnet. If data is 
  aligned, TRUE will be returned.
  
Arguments:

  Address             - The address of the flash map space
  RelativeAddress     - The relative address of the Buffer
  LocType             - The type of the VTF


Returns:

    
--*/
{
  UINT64  TempAddress;
  UINT8   *LocalBuff;

  if (LocType == FIRST_VTF) {
    LocalBuff         = (UINT8 *) Vtf1EndBuffer;
    TempAddress       = Fv1EndAddress - Address;
    *RelativeAddress  = (UINTN) LocalBuff - (UINTN) TempAddress;
  } else {
    LocalBuff         = (UINT8 *) Vtf2EndBuffer;
    TempAddress       = Fv2EndAddress - Address;
    *RelativeAddress  = (UINTN) LocalBuff - (UINTN) TempAddress;
  }
}

EFI_STATUS
GetComponentVersionInfo (
  IN  OUT PARSED_VTF_INFO   *VtfInfo,
  IN      UINT8             *Buffer
  )
/*++
Routine Description:

  This function will extract the version information from File
  
Arguments:

  VtfInfo  - A Pointer to the VTF Info Structure
  Buffer   - A Pointer to type UINT8 

Returns:
 
   EFI_SUCCESS           - The function completed successfully
   EFI_INVALID_PARAMETER - The parameter is invalid
    
--*/
{
  UINT16      VersionInfo;
  EFI_STATUS  Status;

  switch (VtfInfo->CompType) {

  case COMP_TYPE_FIT_PAL_A:
  case COMP_TYPE_FIT_PAL_B:
    memcpy (&VersionInfo, (Buffer + 8), sizeof (UINT16));
    VtfInfo->MajorVer = (UINT8) ((VersionInfo & 0xFF00) >> 8);
    VtfInfo->MinorVer = (UINT8) (VersionInfo & 0x00FF);
    Status            = EFI_SUCCESS;
    break;

  default:
    Status = EFI_INVALID_PARAMETER;
    break;
  }

  return Status;
}

BOOLEAN
CheckAddressAlignment (
  IN      UINT64  Address,
  IN      UINT64  AlignmentData,
  IN OUT  UINT64  *AlignAdjustByte
  )
/*++
  
Routine Description:

  This function checks for the address alignmnet for specified data boundary. In
  case the address is not aligned, it returns FALSE and the amount of data in 
  terms of byte needed to adjust to get the boundary alignmnet. If data is 
  aligned, TRUE will be returned.
  
Arguments:

  Address              - Pointer to buffer containing byte data of component.
  AlignmentData        - DataSize for which address needed to be aligned
  AlignAdjustByte      - Number of bytes needed to adjust alignment.

Returns:

  TRUE                 - Address is aligned to specific data size boundary
  FALSE                - Address in not aligned to specified data size boundary
                       - Add/Subtract AlignAdjustByte to aling the address.
    
--*/
{
  //
  // Check if the assigned address is on address boundary. If not, it will
  // return the remaining byte required to adjust the address for specified
  // address boundary
  //
  *AlignAdjustByte = (Address % AlignmentData);

  if (*AlignAdjustByte == 0) {
    return TRUE;
  } else {
    return FALSE;
  }
}

EFI_STATUS
GetFitTableStartAddress (
  IN OUT  FIT_TABLE   **FitTable
  )
/*++
  
Routine Description:

  Get the FIT table start address in VTF Buffer
  
Arguments:

  FitTable    - Pointer to available fit table where new component can be added
  
Returns:

  EFI_SUCCESS - The function completed successfully
    
--*/
{
  UINT64  FitTableAdd;
  UINT64  FitTableAddOffset;
  UINTN   RelativeAddress;

  //
  // Read the Fit Table address from Itanium-based address map.
  //
  FitTableAddOffset = Fv1EndAddress - (SIZE_IA32_RESET_VECT + SIZE_SALE_ENTRY_POINT + SIZE_FIT_TABLE_ADD);

  //
  // Translate this Itanium-based address in terms of local buffer address which
  // contains the image for Boot Strapped File. The relative address will be
  // the address of fit table VTF buffer.
  //
  GetRelativeAddressInVtfBuffer (FitTableAddOffset, &RelativeAddress, FIRST_VTF);
  FitTableAdd = *(UINTN *) RelativeAddress;

  //
  // The FitTableAdd is the extracted Itanium based address pointing to FIT
  // table. The relative address will return its actual location in VTF
  // Buffer.
  //
  GetRelativeAddressInVtfBuffer (FitTableAdd, &RelativeAddress, FIRST_VTF);

  *FitTable = (FIT_TABLE *) RelativeAddress;

  return EFI_SUCCESS;
}

EFI_STATUS
GetNextAvailableFitPtr (
  IN  FIT_TABLE   **FitPtr
  )
/*++
  
Routine Description:

  Get the FIT table address and locate the free space in fit where we can add
  new component. In this process, this function locates the fit table using
  Fit pointer in Itanium-based address map (as per Intel?Itanium(TM) SAL spec) 
  and locate the available location in FIT table to be used by new components. 
  If there are any Fit table which areg not being used contains ComponentType 
  field as 0x7F. If needed we can change this and spec this out.
  
Arguments:

  FitPtr    - Pointer to available fit table where new component can be added
  
Returns:

  EFI_SUCCESS  - The function completed successfully
    
--*/
{
  FIT_TABLE *TmpFitPtr;
  UINT64    FitTableAdd;
  UINT64    FitTableAddOffset;
  UINTN     Index;
  UINTN     NumFitComponents;
  UINTN     RelativeAddress;

  //
  // Read the Fit Table address from Itanium-based address map.
  //
  FitTableAddOffset = Fv1EndAddress - (SIZE_IA32_RESET_VECT + SIZE_SALE_ENTRY_POINT + SIZE_FIT_TABLE_ADD);

  //
  // Translate this Itanium-based address in terms of local buffer address which
  // contains the image for Boot Strapped File. The relative address will be
  // the address of fit table VTF buffer.
  //
  GetRelativeAddressInVtfBuffer (FitTableAddOffset, &RelativeAddress, FIRST_VTF);
  FitTableAdd = *(UINTN *) RelativeAddress;

  //
  // The FitTableAdd is the extracted Itanium based address pointing to FIT
  // table. The relative address will return its actual location in VTF
  // Buffer.
  //
  GetRelativeAddressInVtfBuffer (FitTableAdd, &RelativeAddress, FIRST_VTF);

  TmpFitPtr         = (FIT_TABLE *) RelativeAddress;
  NumFitComponents  = TmpFitPtr->CompSize;

  for (Index = 0; Index < NumFitComponents; Index++) {
    if ((TmpFitPtr->CvAndType & FIT_TYPE_MASK) == COMP_TYPE_FIT_UNUSED) {
      *FitPtr = TmpFitPtr;
      break;
    }

    TmpFitPtr++;
  }

  return EFI_SUCCESS;
}

INTN
CompareItems (
  IN const VOID  *Arg1,
  IN const VOID  *Arg2
  )
/*++

Routine Description:

    This function is used by qsort to sort the FIT table based upon Component
    Type in their incresing order.

Arguments:
    
    Arg1  -   Pointer to Arg1
    Arg2  -   Pointer to Arg2
    
Returns:

    None

--*/
{
  if ((((FIT_TABLE *) Arg1)->CvAndType & FIT_TYPE_MASK) > (((FIT_TABLE *) Arg2)->CvAndType & FIT_TYPE_MASK)) {
    return 1;
  } else if ((((FIT_TABLE *) Arg1)->CvAndType & FIT_TYPE_MASK) < (((FIT_TABLE *) Arg2)->CvAndType & FIT_TYPE_MASK)) {
    return -1;
  } else {
    return 0;
  }
}

VOID
SortFitTable (
  IN  VOID
  )
/*++

Routine Description:

    This function is used by qsort to sort the FIT table based upon Component
    Type in their incresing order.

Arguments:
    
    VOID

Returns:

    None

--*/
{
  FIT_TABLE *FitTable;
  FIT_TABLE *TmpFitPtr;
  UINTN     NumFitComponents;
  UINTN     Index;

  GetFitTableStartAddress (&FitTable);
  TmpFitPtr         = FitTable;
  NumFitComponents  = 0;
  for (Index = 0; Index < FitTable->CompSize; Index++) {
    if ((TmpFitPtr->CvAndType & FIT_TYPE_MASK) != COMP_TYPE_FIT_UNUSED) {
      NumFitComponents += 1;
    }

    TmpFitPtr++;
  }

  qsort ((VOID *) FitTable, NumFitComponents, sizeof (FIT_TABLE), CompareItems);
}

VOID
UpdateFitEntryForFwVolume (
  IN  UINT64  Size
  )
/*++
  
Routine Description:

  This function updates the information about Firmware Volume  in FIT TABLE.
  This FIT table has to be immediately below the PAL_A Start and it contains
  component type and address information. Other informations can't be
  created this time so we would need to fix it up..
  
  
Arguments:

  Size   - Firmware Volume Size
  
Returns:

  VOID

--*/
{
  FIT_TABLE *CompFitPtr;
  UINTN     RelativeAddress;

  //
  // FV Fit table will be located at PAL_A Startaddress - 16 byte location
  //
  Vtf1LastStartAddress -= 0x10;
  Vtf1TotalSize += 0x10;

  GetRelativeAddressInVtfBuffer (Vtf1LastStartAddress, &RelativeAddress, FIRST_VTF);

  CompFitPtr              = (FIT_TABLE *) RelativeAddress;
  CompFitPtr->CompAddress = Fv1BaseAddress;

  //
  // Since we don't have any information about its location in Firmware Volume,
  // initialize address to 0. This will be updated once Firmware Volume is
  // being build and its current address will be fixed in FIT table. Currently
  // we haven't implemented it so far and working on architectural clarafication
  //
  //
  // Firmware Volume Size in 16 byte block
  //
  CompFitPtr->CompSize = ((UINT32) Size) / 16;

  //
  // Since Firmware Volume does not exist by the time we create this FIT info
  // this should be fixedup from Firmware Volume creation tool. We haven't
  // worked out a method so far.
  //
  CompFitPtr->CompVersion = MAKE_VERSION (0, 0);

  //
  // Since we don't have any info about this file, we are making sure that
  // checksum is not needed.
  //
  CompFitPtr->CvAndType = CV_N_TYPE (0, COMP_TYPE_FIT_FV_BOOT);

  //
  // Since non VTF component will reside outside the VTF, we will not have its
  // binary image while creating VTF, hence we will not perform checksum at
  // this time. Once Firmware Volume is being created which will contain this
  // VTF, it will fix the FIT table for all the non VTF component and hence
  // checksum
  //
  CompFitPtr->CheckSum = 0;
}

EFI_STATUS
UpdateFitEntryForNonVTFComp (
  IN  PARSED_VTF_INFO   *VtfInfo
  )
/*++
  
Routine Description:

  This function updates the information about non VTF component in FIT TABLE.
  Since non VTF componets binaries are not part of VTF binary, we would still
  be required to update its location information in Firmware Volume, inside
  FIT table.
  
Arguments:

  VtfInfo    - Pointer to VTF Info Structure
  
Returns:

  EFI_ABORTED  - The function fails to update the component in FIT  
  EFI_SUCCESS  - The function completed successfully

--*/
{
  FIT_TABLE *CompFitPtr;

  //
  // Scan the FIT table for available space
  //
  GetNextAvailableFitPtr (&CompFitPtr);
  if (CompFitPtr == NULL) {
    printf ("\nERROR: Can't update this component in FIT");
    return EFI_ABORTED;
  }

  //
  // Since we don't have any information about its location in Firmware Volume,
  // initialize address to 0. This will be updated once Firmware Volume is
  // being build and its current address will be fixed in FIT table
  //
  CompFitPtr->CompAddress = 0;
  CompFitPtr->CompSize    = VtfInfo->CompSize;
  CompFitPtr->CompVersion = MAKE_VERSION (VtfInfo->MajorVer, VtfInfo->MinorVer);
  CompFitPtr->CvAndType   = CV_N_TYPE (VtfInfo->CheckSumRequired, VtfInfo->CompType);

  //
  // Since non VTF component will reside outside the VTF, we will not have its
  // binary image while creating VTF, hence we will not perform checksum at
  // this time. Once Firmware Volume is being created which will contain this
  // VTF, it will fix the FIT table for all the non VTF component and hence
  // checksum
  //
  CompFitPtr->CheckSum = 0;

  //
  // Fit Type is FV_BOOT which means Firmware Volume, we initialize this to base
  // address of Firmware Volume in which this VTF will be attached.
  //
  if ((CompFitPtr->CvAndType & 0x7F) == COMP_TYPE_FIT_FV_BOOT) {
    CompFitPtr->CompAddress = Fv1BaseAddress;
  }

  return EFI_SUCCESS;
}

//
// !!!WARNING
// This function is updating the SALE_ENTRY in Itanium address space as per SAL
// spec. SALE_ENTRY is being read from SYM file of PEICORE. Once the PEI
// CORE moves in Firmware Volume, we would need to modify this function to be
// used with a API which will detect PEICORE component while building Firmware
// Volume and update its entry in FIT table as well as in Itanium address space
// as per Intel?Itanium(TM) SAL address space
//
EFI_STATUS
UpdateEntryPoint (
  IN  PARSED_VTF_INFO   *VtfInfo,
  IN  UINT64            *CompStartAddress
  )
/*++
  
Routine Description:

  This function updated the architectural entry point in IPF, SALE_ENTRY.
  
Arguments:

  VtfInfo            - Pointer to VTF Info Structure 
  CompStartAddress   - Pointer to Component Start Address
  
Returns:

  EFI_INVALID_PARAMETER  - The parameter is invalid
  EFI_SUCCESS            - The function completed successfully

--*/
{
  UINTN   RelativeAddress;
  UINT64  SalEntryAdd;
  FILE    *Fp;
  UINTN   Offset;

  CHAR8   Buff[FILE_NAME_SIZE];
  CHAR8   Buff1[10];
  CHAR8   Buff2[10];
  CHAR8   OffsetStr[30];
  CHAR8   Buff3[10];
  CHAR8   Buff4[10];
  CHAR8   Buff5[10];
  CHAR8   Token[50];

  Fp = fopen (VtfInfo->CompSymName, "r+b");

  if (Fp == NULL) {
    printf ("\nERROR: Error in opening file");
    return EFI_INVALID_PARAMETER;
  }
  printf("\n we handle PEI CORE here!");
  while (fgets (Buff, sizeof (Buff), Fp) != NULL) {
    fscanf (
      Fp,
      "%s %s %s %s %s %s %s",
      &Buff1,
      &Buff2,
      &OffsetStr,
      &Buff3,
      &Buff4,
      &Buff5,
      &Token
      );
    if (strnicmp (Token, "SALE_ENTRY", 10) == 0) {
      break;
    }
  }

  Offset = strtoul (OffsetStr, NULL, 16);

  *CompStartAddress += Offset;
  SalEntryAdd = Fv1EndAddress - (SIZE_IA32_RESET_VECT + SIZE_SALE_ENTRY_POINT);

  GetRelativeAddressInVtfBuffer (SalEntryAdd, &RelativeAddress, FIRST_VTF);

  memcpy ((VOID *) RelativeAddress, (VOID *) CompStartAddress, sizeof (UINT64));

  return EFI_SUCCESS;
}

EFI_STATUS
CreateAndUpdateComponent (
  IN  PARSED_VTF_INFO   *VtfInfo
  )
/*++
  
Routine Description:

  This function reads the binary file for each components and update them
  in VTF Buffer as well as in FIT table. If the component is located in non
  VTF area, only the FIT table address will be updated
  
Arguments:

  VtfInfo    - Pointer to Parsed Info
  
Returns:

  EFI_SUCCESS      - The function completed successful
  EFI_ABORTED      - Aborted due to one of the many reasons like:
                      (a) Component Size greater than the specified size.
                      (b) Error opening files.
            
  EFI_INVALID_PARAMETER     Value returned from call to UpdateEntryPoint()
  EFI_OUT_OF_RESOURCES      Memory allocation failure.
  
--*/
{
  EFI_STATUS  Status;
  UINT64      CompStartAddress;
  UINT64      FileSize;
  UINT64      NumByteRead;
  UINT64      NumAdjustByte;
  UINT8       *Buffer;
  FILE        *Fp;
  FIT_TABLE   *CompFitPtr;
  BOOLEAN     Aligncheck;

  if (VtfInfo->LocationType == NONE) {
    printf("\n start to call UpdateFitEntryForNonVTFComp");
    UpdateFitEntryForNonVTFComp (VtfInfo);
    return EFI_SUCCESS;
  }

  Fp = fopen (VtfInfo->CompBinName, "r+b");

  if (Fp == NULL) {
    printf ("\nERROR: Opening file %s", VtfInfo->CompBinName);
    return EFI_ABORTED;
  }

  FileSize = _filelength (fileno (Fp));

  if ((VtfInfo->CompType == COMP_TYPE_FIT_PAL_B) || (VtfInfo->CompType == COMP_TYPE_FIT_PAL_A_SPECIFIC)) {

    //
    // BUGBUG: Satish to correct
    //
    FileSize -= SIZE_OF_PAL_HEADER;
  }

  if (VtfInfo->PreferredSize) {
    if (FileSize > VtfInfo->CompSize) {
      printf ("\nERROR: The component size is more than specified size");
      return EFI_ABORTED;
    }

    FileSize = VtfInfo->CompSize;
  }

  Buffer = malloc ((UINTN) FileSize);
  if (Buffer == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }
  memset (Buffer, 0, (UINTN) FileSize);

  if ((VtfInfo->CompType == COMP_TYPE_FIT_PAL_B) || (VtfInfo->CompType == COMP_TYPE_FIT_PAL_A_SPECIFIC)) {

    //
    // Read first 64 bytes of PAL header and use it to find version info
    //
    NumByteRead = fread (Buffer, sizeof (UINT8), SIZE_OF_PAL_HEADER, Fp);

    //
    // PAL header contains the version info. Currently, we will use the header
    // to read version info and then discard.
    //
    if (!VtfInfo->VersionPresent) {
      GetComponentVersionInfo (VtfInfo, Buffer);
    }
  }

  NumByteRead = fread (Buffer, sizeof (UINT8), (UINTN) FileSize, Fp);
  fclose (Fp);

  //
  // If it is non PAL_B component, pass the entire buffer to get the version
  // info and implement any specific case inside GetComponentVersionInfo.
  //
  if (VtfInfo->CompType != COMP_TYPE_FIT_PAL_B) {
    if (!VtfInfo->VersionPresent) {
      GetComponentVersionInfo (VtfInfo, Buffer);
    }
  }

  if (VtfInfo->LocationType == SECOND_VTF) {

    CompStartAddress = (Vtf2LastStartAddress - FileSize);
  } else {
    CompStartAddress = (Vtf1LastStartAddress - FileSize);
  }

  if (VtfInfo->CompType == COMP_TYPE_FIT_PAL_B) {
    Aligncheck = CheckAddressAlignment (CompStartAddress, 32 * 1024, &NumAdjustByte);
  } else {
    Aligncheck = CheckAddressAlignment (CompStartAddress, 8, &NumAdjustByte);
  }

  if (!Aligncheck) {
    CompStartAddress -= NumAdjustByte;
  }

  if (VtfInfo->LocationType == SECOND_VTF && SecondVTF == TRUE) {
//    printf("\nWe start to Update the second VtfBuffer!");
    Vtf2LastStartAddress = CompStartAddress;
    Vtf2TotalSize += (UINT32) (FileSize + NumAdjustByte);
    printf("\n CompStartAddress is %d", CompStartAddress);
    Status = UpdateVtfBuffer (CompStartAddress, Buffer, FileSize, SECOND_VTF);
  } else if (VtfInfo->LocationType == FIRST_VTF) {
//    printf("\nWe start to Update the first VtfBuffer!");
    Vtf1LastStartAddress = CompStartAddress;
    Vtf1TotalSize += (UINT32) (FileSize + NumAdjustByte);
    Status = UpdateVtfBuffer (CompStartAddress, Buffer, FileSize, FIRST_VTF);
  } else {
    return EFI_INVALID_PARAMETER;
  }

  if (EFI_ERROR (Status)) {
    return EFI_ABORTED;
  }

  GetNextAvailableFitPtr (&CompFitPtr);

  CompFitPtr->CompAddress = CompStartAddress | IPF_CACHE_BIT;
  assert ((FileSize % 16) == 0);
  CompFitPtr->CompSize    = (UINT32) (FileSize / 16);
  CompFitPtr->CompVersion = MAKE_VERSION (VtfInfo->MajorVer, VtfInfo->MinorVer);
  CompFitPtr->CvAndType   = CV_N_TYPE (VtfInfo->CheckSumRequired, VtfInfo->CompType);
  if (VtfInfo->CheckSumRequired) {
    CompFitPtr->CheckSum  = 0;
    CompFitPtr->CheckSum  = CalculateChecksum8 (Buffer, (UINTN) FileSize);
  }

  //
  // Free the buffer
  //
  if (Buffer) {
    free (Buffer);
  }

  //
  // Update the SYM file for this component based on it's start address.
  //
  Status = UpdateSymFile (CompStartAddress, VTF_SYM_FILE, VtfInfo->CompSymName);
  if (EFI_ERROR (Status)) {

    //
    // At this time, SYM files are not required, so continue on error.
    //
  }

  // !!!!!!!!!!!!!!!!!!!!!
  // BUGBUG:
  // This part of the code is a temporary line since PEICORE is going to be inside
  // VTF till we work out how to determine the SALE_ENTRY through it. We will need
  // to clarify so many related questions
  // !!!!!!!!!!!!!!!!!!!!!!!

  if (VtfInfo->CompType == COMP_TYPE_FIT_PEICORE) {
    printf("\n we Start to  UpdateEntryPoint here!");
    Status = UpdateEntryPoint (VtfInfo, &CompStartAddress);
  }

  return Status;
}

EFI_STATUS
CreateAndUpdatePAL_A (
  IN  PARSED_VTF_INFO   *VtfInfo
  )
/*++
  
Routine Description:

  This function reads the binary file for each components and update them
  in VTF Buffer as well as FIT table
  
Arguments:

  VtfInfo    - Pointer to Parsed Info
  
Returns:

  EFI_ABORTED           - Due to one of the following reasons:
                           (a)Error Opening File
                           (b)The PAL_A Size is more than specified size status
                              One of the values mentioned below returned from 
                              call to UpdateSymFile
  EFI_SUCCESS           - The function completed successfully.
  EFI_INVALID_PARAMETER - One of the input parameters was invalid.
  EFI_ABORTED           - An error occurred.UpdateSymFile
  EFI_OUT_OF_RESOURCES  - Memory allocation failed.
   
--*/
{
  EFI_STATUS  Status;
  UINT64      PalStartAddress;
  UINT64      AbsAddress;
  UINTN       RelativeAddress;
  UINT64      FileSize;
  UINT64      NumByteRead;
  UINT8       *Buffer;
  FILE        *Fp;
  FIT_TABLE   *PalFitPtr;

  Fp = fopen (VtfInfo->CompBinName, "r+b");

  if (Fp == NULL) {
    printf ("\nERROR: Opening file %s", VtfInfo->CompBinName);
    return EFI_ABORTED;
  }

  FileSize = _filelength (fileno (Fp));
  FileSize -= SIZE_OF_PAL_HEADER;

  if (VtfInfo->PreferredSize) {
    if (FileSize > VtfInfo->CompSize) {
      printf ("\nERROR: The PAL_A Size is more than specified size");
      return EFI_ABORTED;
    }

    FileSize = VtfInfo->CompSize;
  }

  Buffer = malloc ((UINTN) FileSize);
  if (Buffer == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }
  memset (Buffer, 0, (UINTN) FileSize);

  //
  // Read, Get version Info and discard the PAL header.
  //
  NumByteRead = fread (Buffer, sizeof (UINT8), SIZE_OF_PAL_HEADER, Fp);

  //
  // Extract the version info from header of PAL_A. Once done, discrad this buffer
  //
  if (!VtfInfo->VersionPresent) {
    GetComponentVersionInfo (VtfInfo, Buffer);
  }

  //
  // Read PAL_A file in a buffer
  //
  NumByteRead = fread (Buffer, sizeof (UINT8), (UINTN) FileSize, Fp);
  fclose (Fp);

  PalStartAddress       = Fv1EndAddress - (SIZE_TO_OFFSET_PAL_A_END + FileSize);
  Vtf1LastStartAddress  = PalStartAddress;
  Vtf1TotalSize += (UINT32) FileSize;
  Status      = UpdateVtfBuffer (PalStartAddress, Buffer, FileSize, FIRST_VTF);

  AbsAddress  = Fv1EndAddress - SIZE_TO_PAL_A_FIT;
  GetRelativeAddressInVtfBuffer (AbsAddress, &RelativeAddress, FIRST_VTF);
  PalFitPtr               = (FIT_TABLE *) RelativeAddress;
  PalFitPtr->CompAddress  = PalStartAddress | IPF_CACHE_BIT;
  assert ((FileSize % 16) == 0);
  PalFitPtr->CompSize     = (UINT32) (FileSize / 16);
  PalFitPtr->CompVersion  = MAKE_VERSION (VtfInfo->MajorVer, VtfInfo->MinorVer);
  PalFitPtr->CvAndType    = CV_N_TYPE (VtfInfo->CheckSumRequired, VtfInfo->CompType);
  if (VtfInfo->CheckSumRequired) {
    PalFitPtr->CheckSum = 0;
    PalFitPtr->CheckSum = CalculateChecksum8 (Buffer, (UINTN) FileSize);
  }

  if (Buffer) {
    free (Buffer);
  }

  //
  // Update the SYM file for this component based on it's start address.
  //
  Status = UpdateSymFile (PalStartAddress, VTF_SYM_FILE, VtfInfo->CompSymName);
  if (EFI_ERROR (Status)) {

    //
    // At this time, SYM files are not required, so continue on error.
    //
  }

  return Status;
}

EFI_STATUS
CreateFitTableAndInitialize (
  IN  PARSED_VTF_INFO   *VtfInfo
  )
/*++
  
Routine Description:

  This function creates and intializes FIT table which would be used to
  add component info inside this
  
Arguments:

  VtfInfo    - Pointer to Parsed Info
  
Returns:

  EFI_ABORTED  - Aborted due to no size information
  EFI_SUCCESS  - The function completed successfully

--*/
{
  UINT64    PalFitTableAdd;
  UINT64    FitTableAdd;
  UINT64    FitTableAddressOffset;
  FIT_TABLE *PalFitPtr;
  FIT_TABLE *FitStartPtr;
  UINTN     NumFitComp;
  UINTN     RelativeAddress;
  UINTN     Index;

  if (!VtfInfo->PreferredSize) {
    printf ("\nERROR: FIT could not be allocated becuase there are no size information");
    return EFI_ABORTED;
  }

  if ((VtfInfo->CompSize % 16) != 0) {
    printf ("\nERROR: Invalid Fit Table Size, not multiple of 16 bytes. Please correct the size");
  }

  PalFitTableAdd = Fv1EndAddress - SIZE_TO_PAL_A_FIT;
  GetRelativeAddressInVtfBuffer (PalFitTableAdd, &RelativeAddress, FIRST_VTF);
  PalFitPtr             = (FIT_TABLE *) RelativeAddress;
  PalFitTableAdd        = (PalFitPtr->CompAddress - VtfInfo->CompSize);

  FitTableAdd           = (PalFitPtr->CompAddress - 0x10) - VtfInfo->CompSize;
  FitTableAddressOffset = Fv1EndAddress - (SIZE_IA32_RESET_VECT + SIZE_SALE_ENTRY_POINT + SIZE_FIT_TABLE_ADD);
  GetRelativeAddressInVtfBuffer (FitTableAddressOffset, &RelativeAddress, FIRST_VTF);
  *(UINT64 *) RelativeAddress = FitTableAdd;

  GetRelativeAddressInVtfBuffer (FitTableAdd, &RelativeAddress, FIRST_VTF);

  //
  // Update Fit Table with FIT Signature and FIT info in first 16 bytes.
  //
  FitStartPtr = (FIT_TABLE *) RelativeAddress;
  
  strncpy ((CHAR8 *) &FitStartPtr->CompAddress, FIT_SIGNATURE, 8);  // "_FIT_   "
  assert (((VtfInfo->CompSize & 0x00FFFFFF) % 16) == 0);
  FitStartPtr->CompSize     = (VtfInfo->CompSize & 0x00FFFFFF) / 16;
  FitStartPtr->CompVersion  = MAKE_VERSION (VtfInfo->MajorVer, VtfInfo->MinorVer);

  //
  // BUGBUG: If a checksum is required, add code to checksum the FIT table.  Also
  // determine what to do for things like the FV component that aren't easily checksummed.
  // The checksum will be done once we are done with all the componet update in the FIT
  // table
  //
  FitStartPtr->CvAndType  = CV_N_TYPE (VtfInfo->CheckSumRequired, VtfInfo->CompType);

  NumFitComp              = FitStartPtr->CompSize;

  FitStartPtr++;

  //
  // Intialize remaining FIT table space to UNUSED fit component type
  // so that when we need to create a FIT entry for a component, we can
  // locate a free one and use it.
  //
  for (Index = 0; Index < (NumFitComp - 1); Index++) {
    FitStartPtr->CvAndType = 0x7F;  // Initialize all with UNUSED
    FitStartPtr++;
  }

  Vtf1TotalSize += VtfInfo->CompSize;
  Vtf1LastStartAddress -= VtfInfo->CompSize;

  return EFI_SUCCESS;
}

EFI_STATUS
WriteVtfBinary (
  IN CHAR8     *FileName,
  IN UINT32    VtfSize,
  IN LOC_TYPE  LocType
  )
/*++

Routine Description:

  Write Firmware Volume from memory to a file.
  
Arguments:

  FileName     - Output File Name which needed to be created/
  VtfSize      - FileSize
  LocType      - The type of the VTF
  
Returns:

  EFI_ABORTED - Returned due to one of the following resons:
                 (a) Error Opening File
                 (b) Failing to copy buffers
  EFI_SUCCESS - The fuction completes successfully

--*/
{
  FILE  *Fp;
  UINTN NumByte;
  VOID  *VtfBuffer;
  UINTN RelativeAddress;

  if (LocType == FIRST_VTF) {
    GetRelativeAddressInVtfBuffer (Vtf1LastStartAddress, &RelativeAddress, FIRST_VTF);
    VtfBuffer = (VOID *) RelativeAddress;
  } else {
    GetRelativeAddressInVtfBuffer (Vtf2LastStartAddress, &RelativeAddress, SECOND_VTF);
    VtfBuffer = (VOID *) RelativeAddress;
  }

  Fp = fopen (FileName, "w+b");
  if (Fp == NULL) {
    printf ("Error in opening file %s\n", FileName);
    return EFI_ABORTED;
  }

  NumByte = fwrite (VtfBuffer, sizeof (UINT8), (UINTN) VtfSize, Fp);

  if (Fp) {
    fclose (Fp);
  }

  if (NumByte != (sizeof (UINT8) * VtfSize)) {
    printf ("\nERROR: Could not copy buffer into file %s ", FileName);
    return EFI_ABORTED;
  }

  return EFI_SUCCESS;
}

EFI_STATUS
UpdateVtfBuffer (
  IN  UINT64   StartAddress,
  IN  UINT8    *Buffer,
  IN  UINT64   DataSize,
  IN LOC_TYPE  LocType
  )
/*++

Routine Description:

  Update the Firmware Volume Buffer with requested buffer data
  
Arguments:

  StartAddress   - StartAddress in buffer. This number will automatically
                  point to right address in buffer where data needed 
                  to be updated.
  Buffer         - Buffer pointer from data will be copied to memory mapped buffer.
  DataSize       - Size of the data needed to be copied.
  LocType        - The type of the VTF: First or Second

Returns:
  
  EFI_ABORTED  - The input parameter is error
  EFI_SUCCESS  - The function completed successfully

--*/
{
  UINT8 *LocalBufferPtrToWrite;

  if (LocType == FIRST_VTF) {
    if ((StartAddress | IPF_CACHE_BIT) < (Vtf1LastStartAddress | IPF_CACHE_BIT)) {
      printf ("ERROR: Start Address is less then the VTF start address\n");
      return EFI_ABORTED;
    }

    LocalBufferPtrToWrite = (UINT8 *) Vtf1EndBuffer;
//    printf("\n %d", LocalBufferPtrToWrite);
    LocalBufferPtrToWrite -= (Fv1EndAddress - StartAddress);
//    printf("\nLocalBufferPtrToWrite is %d", LocalBufferPtrToWrite);
  } else {
//    printf("\nWe now in processing the second VTF!");
    if ((StartAddress | IPF_CACHE_BIT) < (Vtf2LastStartAddress | IPF_CACHE_BIT)) {
//      printf ("ERROR: Start Address is less then the VTF start address\n");
      return EFI_ABORTED;
    }
    LocalBufferPtrToWrite = (UINT8 *) Vtf2EndBuffer;
//    printf("\n %d", LocalBufferPtrToWrite);
    LocalBufferPtrToWrite -= (Fv2EndAddress - StartAddress);
//    printf("\n %d", LocalBufferPtrToWrite);
  }
  
  printf("\n Buffer is %d", *Buffer);
  memcpy (LocalBufferPtrToWrite, Buffer, (UINTN) DataSize);

  return EFI_SUCCESS;
}

EFI_STATUS
UpdateFfsHeader (
  IN UINT32         TotalVtfSize,
  IN LOC_TYPE       LocType  
  )
/*++

Routine Description:

  Update the Firmware Volume Buffer with requested buffer data
  
Arguments:

  TotalVtfSize     - Size of the VTF
  Fileoffset       - The start of the file relative to the start of the FV.
  LocType          - The type of the VTF

Returns:
  
  EFI_SUCCESS            - The function completed successfully
  EFI_INVALID_PARAMETER  - The Ffs File Header Pointer is NULL

--*/
{
  EFI_FFS_FILE_HEADER *FileHeader;
  UINTN               RelativeAddress;
  EFI_GUID            EfiFirmwareVolumeTopFileGuid = EFI_FFS_VOLUME_TOP_FILE_GUID;

  //
  // Find the VTF file header location
  //
  if (LocType == FIRST_VTF) {
    GetRelativeAddressInVtfBuffer (Vtf1LastStartAddress, &RelativeAddress, FIRST_VTF);
    FileHeader = (EFI_FFS_FILE_HEADER *) RelativeAddress;
  } else {
    GetRelativeAddressInVtfBuffer (Vtf2LastStartAddress, &RelativeAddress, SECOND_VTF);
    FileHeader = (EFI_FFS_FILE_HEADER *) RelativeAddress;
  }

  if (FileHeader == NULL) {
    return EFI_INVALID_PARAMETER;
  }

  //
  // write header
  //
  memset (FileHeader, 0, sizeof (EFI_FFS_FILE_HEADER));
  memcpy (&FileHeader->Name, &EfiFirmwareVolumeTopFileGuid, sizeof (EFI_GUID));
  FileHeader->Type        = EFI_FV_FILETYPE_FREEFORM;
  FileHeader->Attributes  = FFS_ATTRIB_CHECKSUM;

  //
  // Now FileSize includes the EFI_FFS_FILE_HEADER
  //
  FileHeader->Size[0] = (UINT8) (TotalVtfSize & 0x000000FF);
  FileHeader->Size[1] = (UINT8) ((TotalVtfSize & 0x0000FF00) >> 8);
  FileHeader->Size[2] = (UINT8) ((TotalVtfSize & 0x00FF0000) >> 16);

  //
  // Fill in checksums and state, all three must be zero for the checksums.
  //
  FileHeader->IntegrityCheck.Checksum.Header  = 0;
  FileHeader->IntegrityCheck.Checksum.File    = 0;
  FileHeader->State                           = 0;
  FileHeader->IntegrityCheck.Checksum.Header  = CalculateChecksum8 ((UINT8 *) FileHeader, sizeof (EFI_FFS_FILE_HEADER));
  printf("\nDone for udpate header checksum");
  printf("\nTotalVtfSize is %d", TotalVtfSize);
  FileHeader->IntegrityCheck.Checksum.File    = CalculateChecksum8 ((UINT8 *) FileHeader, TotalVtfSize);
  printf("\nDone for udpate File checksum");
  FileHeader->State                           = EFI_FILE_HEADER_CONSTRUCTION | EFI_FILE_HEADER_VALID | EFI_FILE_DATA_VALID;

  return EFI_SUCCESS;
}

EFI_STATUS
ValidateAddressAndSize (
  IN  UINT64  BaseAddress,
  IN  UINT64  FwVolSize
  )
/*++

Routine Description:

  Update the Firmware Volume Buffer with requested buffer data
  
Arguments:

  BaseAddress    - Base address for the Fw Volume.
  
  FwVolSize      - Total Size of the FwVolume to which VTF will be attached..

Returns:
  
  EFI_SUCCESS     - The function completed successfully
  EFI_UNSUPPORTED - The input parameter is error

--*/
{
  if ((BaseAddress >= 0) && (FwVolSize > 0x40) && ((BaseAddress + FwVolSize) % 8 == 0)) {
    return EFI_SUCCESS;
  }

  return EFI_UNSUPPORTED;
}

EFI_STATUS
UpdateIA32ResetVector (
  IN  CHAR8   *FileName,
  IN  UINT64  FirstFwVSize
  )
/*++

Routine Description:

  Update the 16 byte IA32 Reset vector to maintain the compatibility
  
Arguments:

  FileName     - Binary file name which contains the IA32 Reset vector info..
  FirstFwVSize - Total Size of the FwVolume to which VTF will be attached..

Returns:
  
  EFI_SUCCESS            - The function completed successfully
  EFI_ABORTED            - Invalid File Size
  EFI_INVALID_PARAMETER  - Bad File Name
  EFI_OUT_OF_RESOURCES   - Memory allocation failed.

--*/
{
  UINT8 *Buffer;
  UINT8 *LocalVtfBuffer;
  UINTN FileSize;
  UINTN NumByteRead;
  FILE  *Fp;

  if (!strcmp (FileName, "")) {
    return EFI_INVALID_PARAMETER;
  }

  Fp = fopen (FileName, "r+b");

  if (Fp == NULL) {
    printf ("\nERROR: Unable to open the file %s", FileName);
  }

  FileSize = _filelength (fileno (Fp));

  if (FileSize > 16) {
    return EFI_ABORTED;
  }

  Buffer = malloc (FileSize);
  if (Buffer == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }

  NumByteRead     = fread (Buffer, sizeof (UINT8), FileSize, Fp);

  LocalVtfBuffer  = (UINT8 *) Vtf1EndBuffer - SIZE_IA32_RESET_VECT;
  memcpy (LocalVtfBuffer, Buffer, FileSize);

  if (Buffer) {
    free (Buffer);
  }

  return EFI_SUCCESS;
}

VOID
CleanUpMemory (
  VOID
  )
/*++

Routine Description:

  This function cleans up any allocated buffer
  
Arguments:

  NONE

Returns:
  
  NONE

--*/
{
  PARSED_VTF_INFO *TempFileListPtr;

  if (Vtf1Buffer) {
    free (Vtf1Buffer);
  }

  if (Vtf2Buffer) {
    free (Vtf2Buffer);
  }

  //
  // Cleanup the buffer which was allocated to read the file names from FV.INF
  //
  FileListPtr = FileListHeadPtr;
  while (FileListPtr != NULL) {
    TempFileListPtr = FileListPtr->NextVtfInfo;
    free (FileListPtr);
    FileListPtr = TempFileListPtr;
  }
}

EFI_STATUS
ProcessAndCreateVtf (
  IN  UINT64  Size
  )
/*++

Routine Description:

  This function process the link list created during INF file parsing
  and create component in VTF and updates its info in FIT table
  
Arguments:

  Size   - Size of the Firmware Volume of which, this VTF belongs to.

Returns:
  
  EFI_UNSUPPORTED - Unknown FIT type
  EFI_SUCCESS     - The function completed successfully                 

--*/
{
  EFI_STATUS      Status;
  PARSED_VTF_INFO *ParsedInfoPtr;

  Status        = EFI_SUCCESS;

  ParsedInfoPtr = FileListHeadPtr;

  while (ParsedInfoPtr != NULL) {

    switch (ParsedInfoPtr->CompType) {
    //
    // COMP_TYPE_FIT_HEADER is a special case, hence handle it here
    //
    case COMP_TYPE_FIT_HEADER:
      //COMP_TYPE_FIT_HEADER          0x00
      printf("\nStart to call CreateFitTableAndInitialize!");
      Status = CreateFitTableAndInitialize (ParsedInfoPtr);
      break;

    //
    // COMP_TYPE_FIT_PAL_A is a special case, hence handle it here
    //
    case COMP_TYPE_FIT_PAL_A:
      //COMP_TYPE_FIT_PAL_A           0x0F
      printf("\nStart to call CreateAndUpdatePAL_A!");
      Status = CreateAndUpdatePAL_A (ParsedInfoPtr);

      //
      // Based on VTF specification, once the PAL_A component has been written,
      // update the Firmware Volume info as FIT table. This will be utilized
      // to extract the Firmware Volume Start address where this VTF will be
      // of part.
      //
      if (Status == EFI_SUCCESS) {
        UpdateFitEntryForFwVolume (Size);
      }
      break;

    case COMP_TYPE_FIT_FV_BOOT:
      //COMP_TYPE_FIT_FV_BOOT         0x7E
      printf("\nStart to call COMP_TYPE_FIT_FV_BOOT!");
      //
      // Since FIT entry for Firmware Volume has been created and it is
      // located at (PAL_A start - 16 byte). So we will not process any
      // Firmware Volume related entry from INF file
      //
      Status = EFI_SUCCESS;
      break;

    default:
      printf("\nDefault is to CreateAndUpdateComponent!");
      //
      // Any other component type should be handled here. This will create the
      // image in specified VTF and create appropriate entry about this
      // component in FIT Entry.
      //
      Status = CreateAndUpdateComponent (ParsedInfoPtr);
      if (EFI_ERROR (Status)) {
        printf ("ERROR: Updating %s component.\n", ParsedInfoPtr->CompName);
      }
      break;
    }

    ParsedInfoPtr = ParsedInfoPtr->NextVtfInfo;
  }

  return Status;
}

EFI_STATUS
GenerateVtfImage (
  IN  UINT64  StartAddress1,
  IN  UINT64  Size1,
  IN  UINT64  StartAddress2,
  IN  UINT64  Size2,
  IN  FILE    *fp
  )
/*++

Routine Description:

  This is the main function which will be called from application.

Arguments:

  StartAddress1  - The start address of the first VTF      
  Size1          - The size of the first VTF
  StartAddress2  - The start address of the second VTF      
  Size2          - The size of the second VTF
  fp             - The pointer to BSF inf file

Returns:
 
  EFI_OUT_OF_RESOURCES - Can not allocate memory
  The return value can be any of the values 
  returned by the calls to following functions:
      GetVtfRelatedInfoFromInfFile
      ProcessAndCreateVtf
      UpdateIA32ResetVector
      UpdateFfsHeader
      WriteVtfBinary
  
--*/
{
  EFI_STATUS  Status;
//  CHAR8       OutFileName1[FILE_NAME_SIZE];
//  CHAR8       OutFileName2[FILE_NAME_SIZE];
//  BOOLEAN     SecondVTF;
  FILE        *VtfFP;

  Status          = EFI_UNSUPPORTED;
  VtfFP = fp;
  
  if (StartAddress2 == 0) {
//    printf("\nSecondVTF is false!");
    SecondVTF = FALSE;
  } else {
    SecondVTF = TRUE;
  }
  
//  printf("\nSecondVTF is %d", SecondVTF);
  Fv1BaseAddress        = StartAddress1;
  Fv1EndAddress         = Fv1BaseAddress + Size1;
  
//  memset (OutFileName1, 0, FILE_NAME_SIZE);
  //
  // if output file name specified
  //
  if (VTF_OUTPUT) {
    //sprintf(OutFileName1, "%s", VTF_OUTPUT_FILE);
    printf("\nThe first VTF output file is %s", OutFileName1);
    printf("\nThe second VTF output file is %s", OutFileName2);
  }
  //
  // else if output file name not specified, then use the default one
  //
  else {
  sprintf (
    OutFileName1,
    "%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x-%s",
    Vtf1NameGuid.Data1,
    Vtf1NameGuid.Data2,
    Vtf1NameGuid.Data3,
    Vtf1NameGuid.Data4[0],
    Vtf1NameGuid.Data4[1],
    Vtf1NameGuid.Data4[2],
    Vtf1NameGuid.Data4[3],
    Vtf1NameGuid.Data4[4],
    Vtf1NameGuid.Data4[5],
    Vtf1NameGuid.Data4[6],
    Vtf1NameGuid.Data4[7],
    VTF_OUTPUT_FILE
    );
    }
  //
  // The image buffer for the First VTF
  //
  Vtf1Buffer = malloc ((UINTN) Size1);
  if (Vtf1Buffer == NULL) {
    printf ("\nERROR: Not enough resource to create memory mapped file for Boot Strap File");
    return EFI_OUT_OF_RESOURCES;
  }
  memset (Vtf1Buffer, 0x00, (UINTN) Size1);
  Vtf1EndBuffer         = (UINT8 *) Vtf1Buffer + Size1;
//  printf("\n %d", Size1);
//  printf("\n %d", Vtf1Buffer);
  Vtf1LastStartAddress  = Fv1EndAddress | IPF_CACHE_BIT;
  
  if (SecondVTF) {
    Fv2BaseAddress        = StartAddress2;
    Fv2EndAddress         = Fv2BaseAddress + Size2;
    
//    memset (OutFileName2, 0, FILE_NAME_SIZE);
/*
    sprintf (
      OutFileName2,
      "%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x-%s",
      Vtf2NameGuid.Data1,
      Vtf2NameGuid.Data2,
      Vtf2NameGuid.Data3,
      Vtf2NameGuid.Data4[0],
      Vtf2NameGuid.Data4[1],
      Vtf2NameGuid.Data4[2],
      Vtf2NameGuid.Data4[3],
      Vtf2NameGuid.Data4[4],
      Vtf2NameGuid.Data4[5],
      Vtf2NameGuid.Data4[6],
      Vtf2NameGuid.Data4[7],
      VTF_OUTPUT_FILE
      );
*/    
    //
    // The image buffer for the second VTF
    //
    Vtf2Buffer = malloc ((UINTN) Size2);
    if (Vtf2Buffer == NULL) {
      printf ("\nERROR: Not enough resource to create memory mapped file for Boot Strap File");
      return EFI_OUT_OF_RESOURCES;
    }
    memset (Vtf2Buffer, 0x00, (UINTN) Size2);
    Vtf2EndBuffer         = (UINT8 *) Vtf2Buffer + Size2;
    Vtf2LastStartAddress  = Fv2EndAddress | IPF_CACHE_BIT;
  }
  
//  Status = GetVtfRelatedInfoFromInfFile (VTF_INPUT_FILE);
//  printf("\nStart to call GetVtfRelatedInfoFromInfFile!");
  Status = GetVtfRelatedInfoFromInfFile (VtfFP);
  if (Status != EFI_SUCCESS) {
    printf ("\nERROR: Error in parsing input file");
    CleanUpMemory ();
    return Status;
  }

//  printf("\nStart to call ProcessAndCreateVtf!");
//  printf("\n Size1 to call ProcessAndCreateVtf is %d", Size1);
  Status = ProcessAndCreateVtf (Size1);
  if (Status != EFI_SUCCESS) {
    CleanUpMemory ();
    return Status;
  }
  
  printf("\n Done for ProcessAndCreateVtf");
  Status = UpdateIA32ResetVector (IA32BinFile, Vtf1TotalSize);
  if (Status != EFI_SUCCESS) {
    CleanUpMemory ();
    return Status;
  }

  //
  // Re arrange the FIT Table for Ascending order of their FIT Type..
  //
  SortFitTable ();

  //
  // All components have been updated in FIT table. Now perform the FIT table
  // checksum. The following function will check if Checksum is required,
  // if yes, then it will perform the checksum otherwise not.
  //
  CalculateFitTableChecksum ();
  printf("\n Done for CalculateFitTableChecksum");
  //
  // Write the FFS header
  //
  Vtf1TotalSize += sizeof (EFI_FFS_FILE_HEADER);
  Vtf1LastStartAddress -= sizeof (EFI_FFS_FILE_HEADER);
  printf("\nVtf1TotalSize before call UpdateFfsHeader is %d", Vtf1TotalSize);
  Status = UpdateFfsHeader (Vtf1TotalSize, FIRST_VTF);
  if (Status != EFI_SUCCESS) {
    CleanUpMemory ();
    return Status;
  }
  //
  // Update the VTF buffer into specified VTF binary file
  //
  Status  = WriteVtfBinary (OutFileName1, Vtf1TotalSize, FIRST_VTF);

  if (SecondVTF) {
    printf("\n Start to write second vtf");
    Vtf2TotalSize += sizeof (EFI_FFS_FILE_HEADER);
    Vtf2LastStartAddress -= sizeof (EFI_FFS_FILE_HEADER);
    Status = UpdateFfsHeader (Vtf2TotalSize, SECOND_VTF);
    if (Status != EFI_SUCCESS) {
      CleanUpMemory ();
      return Status;
    }
    
    //
    // Update the VTF buffer into specified VTF binary file
    //
    Status  = WriteVtfBinary (OutFileName2, Vtf2TotalSize, SECOND_VTF);
  }
  
  CleanUpMemory ();
  printf ("\n");

  return Status;
}

EFI_STATUS
PeimFixupInFitTable (
  IN  UINT64  StartAddress
  )
/*++

Routine Description:

  This function is an entry point to fixup SAL-E entry point.

Arguments:

  StartAddress - StartAddress for PEIM.....
    
Returns:
 
  EFI_SUCCESS          - The function completed successfully
  EFI_ABORTED          - Error Opening File
  EFI_OUT_OF_RESOURCES - System out of resources for memory allocation.

--*/
{
  EFI_STATUS  Status;
  FILE        *Fp;
  UINT64      *StartAddressPtr;
  UINTN       FirstFwVSize;
  UINTN       NumByte;
//  CHAR8       OutFileName1[FILE_NAME_SIZE];

  StartAddressPtr   = malloc (sizeof (UINT64));
  if (StartAddressPtr == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }
  *StartAddressPtr = StartAddress;

//  memset (OutFileName1, 0, FILE_NAME_SIZE);

  sprintf (
    OutFileName1,
    "%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x-%s",
    Vtf1NameGuid.Data1,
    Vtf1NameGuid.Data2,
    Vtf1NameGuid.Data3,
    Vtf1NameGuid.Data4[0],
    Vtf1NameGuid.Data4[1],
    Vtf1NameGuid.Data4[2],
    Vtf1NameGuid.Data4[3],
    Vtf1NameGuid.Data4[4],
    Vtf1NameGuid.Data4[5],
    Vtf1NameGuid.Data4[6],
    Vtf1NameGuid.Data4[7],
    VTF_OUTPUT_FILE
    );

  Fp = fopen (OutFileName1, "r+b");

  if (Fp == NULL) {
    printf ("\nERROR: Error opening file ");
    if (StartAddressPtr) {
      free (StartAddressPtr);
    }

    return EFI_ABORTED;
  }

  FirstFwVSize = _filelength (fileno (Fp));
  fseek (Fp, (long) (FirstFwVSize - (UINTN) (SIZE_IA32_RESET_VECT + SIZE_SALE_ENTRY_POINT)), SEEK_SET);
  NumByte = fwrite ((VOID *) StartAddressPtr, sizeof (UINT64), 1, Fp);

  if (Fp) {
    fclose (Fp);
  }

  if (StartAddressPtr) {
    free (StartAddressPtr);
  }

  printf ("\n");
  Status = EFI_SUCCESS;
  return Status;
}

EFI_STATUS
UpdateSymFile (
  IN UINT64 BaseAddress,
  IN CHAR8  *DestFileName,
  IN CHAR8  *SourceFileName
  )
/*++

Routine Description:

  This function adds the SYM tokens in the source file to the destination file.
  The SYM tokens are updated to reflect the base address.

Arguments:

  BaseAddress    - The base address for the new SYM tokens.
  DestFileName   - The destination file.
  SourceFileName - The source file.

Returns:

  EFI_SUCCESS             - The function completed successfully.
  EFI_INVALID_PARAMETER   - One of the input parameters was invalid.
  EFI_ABORTED             - An error occurred.

--*/
{
  FILE    *SourceFile;
  FILE    *DestFile;
  CHAR8   Buffer[_MAX_PATH];
  CHAR8   Type[_MAX_PATH];
  CHAR8   Address[_MAX_PATH];
  CHAR8   Section[_MAX_PATH];
  CHAR8   Token[_MAX_PATH];
  CHAR8   BaseToken[_MAX_PATH];
  UINT64  TokenAddress;
  long    StartLocation;

  //
  // Verify input parameters.
  //
  if (BaseAddress == 0 || DestFileName == NULL || SourceFileName == NULL) {
    return EFI_INVALID_PARAMETER;
  }

  //
  // Open the source file
  //
  SourceFile = fopen (SourceFileName, "r");
  if (SourceFile == NULL) {

    //
    // SYM files are not required.
    //
    return EFI_SUCCESS;
  }

  //
  // Use the file name minus extension as the base for tokens
  //
  strcpy (BaseToken, SourceFileName);
  strtok (BaseToken, ". \t\n");
  strcat (BaseToken, "__");

  //
  // Open the destination file
  //
  DestFile = fopen (DestFileName, "a+");
  if (DestFile == NULL) {
    fclose (SourceFile);
    return EFI_ABORTED;
  }

  //
  // If this is the beginning of the output file, write the symbol format info.
  //
  if (fseek (DestFile, 0, SEEK_END) != 0) {
    fclose (SourceFile);
    fclose (DestFile);
    return EFI_ABORTED;
  }

  StartLocation = ftell (DestFile);

  if (StartLocation == 0) {
    fprintf (DestFile, "TEXTSYM format | V1.0\n");
  } else if (StartLocation == -1) {
    fclose (SourceFile);
    fclose (DestFile);
    return EFI_ABORTED;
  }

  //
  // Read the first line
  //
  if (fgets (Buffer, _MAX_PATH, SourceFile) == NULL) {
    Buffer[0] = 0;
  }

  //
  // Make sure it matches the expected sym format
  //
  if (strcmp (Buffer, "TEXTSYM format | V1.0\n")) {
    fclose (SourceFile);
    fclose (DestFile);
    return EFI_ABORTED;
  }

  //
  // Read in the file
  //
  while (feof (SourceFile) == 0) {

    //
    // Read a line
    //
    if (fscanf (SourceFile, "%s | %s | %s | %s\n", Type, Address, Section, Token) == 4) {

      //
      // Get the token address
      //
      AsciiStringToUint64 (Address, TRUE, &TokenAddress);

      //
      // Add the base address, the size of the FFS file header and the size of the peim header.
      //
      TokenAddress += BaseAddress &~IPF_CACHE_BIT;

      fprintf (DestFile, "%s | %016I64X | %s | %s%s\n", Type, TokenAddress, Section, BaseToken, Token);
    }
  }

  fclose (SourceFile);
  fclose (DestFile);
  return EFI_SUCCESS;
}

EFI_STATUS
CalculateFitTableChecksum (
  VOID
  )
/*++
  
Routine Description:

  This function will perform byte checksum on the FIT table, if the the checksum required
  field is set to CheckSum required. If the checksum is not required then checksum byte
  will have value as 0;.
  
Arguments:

  NONE
  
Returns:

  Status       - Value returned by call to CalculateChecksum8 ()
  EFI_SUCCESS  - The function completed successfully
    
--*/
{
  FIT_TABLE *TmpFitPtr;
  UINT64    FitTableAdd;
  UINT64    FitTableAddOffset;
  UINTN     RelativeAddress;
  UINTN     Size;

  //
  // Read the Fit Table address from Itanium-based address map.
  //
  FitTableAddOffset = Fv1EndAddress - (SIZE_IA32_RESET_VECT + SIZE_SALE_ENTRY_POINT + SIZE_FIT_TABLE_ADD);

  //
  // Translate this Itanium-based address in terms of local buffer address which
  // contains the image for Boot Strapped File
  //
  GetRelativeAddressInVtfBuffer (FitTableAddOffset, &RelativeAddress, FIRST_VTF);
  FitTableAdd = *(UINTN *) RelativeAddress;

  GetRelativeAddressInVtfBuffer (FitTableAdd, &RelativeAddress, FIRST_VTF);

  TmpFitPtr = (FIT_TABLE *) RelativeAddress;

  Size      = TmpFitPtr->CompSize * 16;

  if ((TmpFitPtr->CvAndType & CHECKSUM_BIT_MASK) >> 7) {
    TmpFitPtr->CheckSum = 0;
    TmpFitPtr->CheckSum = CalculateChecksum8 ((UINT8 *) TmpFitPtr, Size);
  } else {
    TmpFitPtr->CheckSum = 0;
  }

  return EFI_SUCCESS;
}

VOID
Version (
  VOID
  )
/*++

Routine Description:

  Displays the standard utility information to SDTOUT

Arguments:

  None

Returns:

  None

--*/
{
  printf (
    "%s, EFI 2.0 BootStrap File Generation Utility. Version %i.%i.\n",
    UTILITY_NAME,
    UTILITY_MAJOR_VERSION,
    UTILITY_MINOR_VERSION
    );
}

VOID
Usage (
  VOID
  )
/*++

Routine Description:

  Displays the utility usage syntax to STDOUT

Arguments:

  None

Returns:

  None

--*/
{
  Version();
  
//  printf (
//    "\nUsage: %s -a Arch -o OutPutFile -f FileName -r BaseAddress -s FwVolumeSize\
//    -v Verbose -q Quiet -d DebugLevel -h\n",
//    UTILITY_NAME
//    );
  printf (
    "\nUsage: %s [-o OutPutFile -f FileName -r BaseAddress -s FwVolumeSize]\n",
    UTILITY_NAME
    );
  printf (
    "\nUsage: %s [-o OutPutFile1 -o OutPutFile2 -f FileName -r FirstVTFBaseAddress -s FirstVTFFwVolumeSize -r SecondVTFBaseAddress -s SecondVTFFwVolumeSize]\n",
    UTILITY_NAME
    );  
  printf ("  Where:\n");
//  Only Support IPF now
//  printf ("  Arch is Platform architecture\n");
//  OutPutFile name is GUID-Vtf.RAW
  printf ("  OutPutFile is Filename that will be created\n");
  printf ("  File Name is Name of the BS Image INF file to use\n");
  printf ("  BaseAddress is the starting address of Firmware Volume where Boot\n");
  printf ("  Strapped Image will reside.\n");
  printf ("  FwVolumeSize is the size of Firmware Volume.\n");
//  printf ("  Verbose output\n");
//  printf ("  Quiet is to disable all messages except FATAL ERRORS\n");
//  printf ("  DebugLevel is to enable debug message at level #\n");
  printf ("  Print copyright,version and usage of this program and exit code: PASS\n");
}

EFI_STATUS
main (
  IN UINTN  argc,
  IN  CHAR8 **argv
  )
/*++

Routine Description:

  This utility uses GenVtf.dll to build a Boot Strap File Image which will be
  part of firmware volume image.

Arguments:

  argc   - The count of the parameters
  argv   - The parameters


Returns:

  0   - No error conditions detected.
  1   - One or more of the input parameters is invalid.
  2   - A resource required by the utility was unavailable.  
      - Most commonly this will be memory allocation or file creation.
  3   - GenFvImage.dll could not be loaded.
  4   - Error executing the GenFvImage dll.
  5   - Now this tool does not support the IA32 platform

--*/
{
  UINT8       Index;
  UINT64      StartAddress1;
  UINT64      StartAddress2;
  UINT64      FwVolSize1;
  UINT64      FwVolSize2;
  BOOLEAN     FirstRoundO;
  BOOLEAN     FirstRoundB;
  BOOLEAN     FirstRoundS;
  EFI_STATUS  Status;
  BOOLEAN     IsIA32;
  FILE        *VtfFP;
  CHAR8       *OutputFileName;
  CHAR8       *VtfFileName;


  VtfFP = NULL;
  //
  // Verify the correct number of IA32 arguments
  //
  IsIA32 = FALSE;
  if (argc == IA32_ARGS) {
    //
    //  Now this tool is not used for IA32 platform, if it will be used in future,
    //  the IA32-specific functions need to be updated and verified, the updating can  
    //  refer to IPF relevant functions)
    //
    printf ("ERROR: Now this tool does not support the IA32 platform!\n");
    printf ("ERROR: And the IA32-specific functions need to be updated and verified!\n");
    return 5;
    
    /*
    StartAddress1 = 0;
    IsIA32        = TRUE;

    //
    // Parse the command line arguments
    //
    for (Index = 1; Index < IA32_ARGS; Index += 2) {

      //
      // Make sure argument pair begin with - or /
      //
      if (argv[Index][0] != '-' && argv[Index][0] != '/') {
        Usage ();
        printf ("ERROR: Argument pair must begin with \"-\" or \"/\"\n");
        return 1;
      }

      //
      // Make sure argument specifier is only one letter
      //
      if (argv[Index][2] != 0) {
        Usage ();
        printf ("ERROR: Unrecognized argument \"%s\".\n", argv[Index]);
        return 1;
      }

      //
      // Determine argument to read
      //
      switch (argv[Index][1]) {

      case 't':
      case 'T':
        Status = AsciiStringToUint64 (argv[Index + 1], FALSE, &StartAddress1);
        if (Status != EFI_SUCCESS) {
          printf ("\nERROR: Bad start of address \"%s\"\n", argv[Index + 1]);
          return 1;
        }
        break;

      default:
        Usage ();
        printf ("Unrecognized IA32 argument \"%s\".\n", argv[Index]);
        IsIA32 = FALSE;
        break;
      }
    }

    if (IsIA32) {
      //
      // Call the GenVtfImage 
      //
      Status = Generate32VtfImage (StartAddress1);

      if (EFI_ERROR(Status)) {
        switch (Status) {

        case EFI_INVALID_PARAMETER:
          printf ("\nERROR: Invalid parameter passed to GenVtfImage function .\n");
          break;

        case EFI_ABORTED:
          printf ("\nERROR: Error detected while creating the file image.\n");
          break;

        case EFI_OUT_OF_RESOURCES:
          printf ("\nERROR: GenVtfImage function could not allocate required resources.\n");
          break;

        case EFI_VOLUME_CORRUPTED:
          printf ("\nERROR: No base address was specified \n");
          break;

        default:
          printf ("\nERROR: GenVtfImage function returned unknown status %X.\n", Status);
          break;
        }
        return 2;
      }

      return 0;
    }
    */
  } 

  //
  // Verify the correct number of arguments
  //
  if (argc == 1) {
    Usage();
    return 1;
  }
  
  if ((strcmp(argv[1], "-h") == 0) || (strcmp(argv[1], "--help") == 0) || 
      (strcmp(argv[1], "-?") == 0) || (strcmp(argv[1], "/?") == 0)) {
    Usage();
    return 1;
  }
  
  if ((strcmp(argv[1], "-V") == 0) || (strcmp(argv[1], "--version") == 0)) {
    Version();
    return 1;
  }
 
  if (argc != ONE_VTF_ARGS && argc != TWO_VTF_ARGS && argc != THREE_VTF_ARGS && argc != FOUR_VTF_ARGS) {
    Usage ();
    return 1;
  }

  //
  // Initialize variables
  //
  StartAddress1 = 0;
  StartAddress2 = 0;
  FwVolSize1    = 0;
  FwVolSize2    = 0;
  FirstRoundB   = TRUE;
  FirstRoundS   = TRUE;
  FirstRoundO   = TRUE;
  OutFileName1  = NULL;
  OutFileName2  = NULL;
  
//  memset (OutFileName1, 0, FILE_NAME_SIZE);
//  memset (OutFileName2, 0, FILE_NAME_SIZE);
  //
  // Parse the command line arguments
  //
  for (Index = 1; Index < argc; Index += 2) {

    //
    // Make sure argument pair begin with - or /
    //
    if (argv[Index][0] != '-' && argv[Index][0] != '/') {
      Usage ();
      printf ("ERROR: Argument pair must begin with \"-\" or \"/\"\n");
      return 1;
    }

    //
    // Make sure argument specifier is only one letter
    //
    if (argv[Index][2] != 0) {
      Usage ();
      printf ("ERROR: Unrecognized argument \"%s\".\n", argv[Index]);
      return 1;
    }

    //
    // Determine argument to read
    //
    switch (argv[Index][1]) {
    
    case 'O':
    case 'o':
    //
    // Get the output file name
    //
    VTF_OUTPUT = TRUE;
    if (FirstRoundO) {
    //
    // It's the first output file name
    //
    //strncpy(OutFileName1, argv[Index+1], FILE_NAME_SIZE);
    OutFileName1 = (CHAR8 *)argv[Index+1];
    printf("\nOutFileName1 is %s", OutFileName1);
    FirstRoundO = FALSE;
    }
    else {
    //
    //
    //
    //strncpy(OutFileName2, argv[Index+1], FILE_NAME_SIZE);
    OutFileName2 = (CHAR8 *)argv[Index+1];
    printf("\nOutFileName2 is %s", OutFileName2);
    }
    break;
    
    case 'F':
    case 'f':
    //
    // Get the input VTF file name
    // 
//    printf("\ninput file name specified!\n");    
    VtfFileName = argv[Index+1];
    printf("\nBSF inf file is %s", VtfFileName);
    VtfFP = fopen(VtfFileName, "rb");
    if (VtfFP == NULL) {
      printf("\nERROR to open VTF inf file!");
      return 1;
    }
    break;
    
    case 'R':
    case 'r':
//    printf("\nBase address specified!\n");
      if (FirstRoundB) {
//        printf("\nthe first round!\n");
//	      printf("\n%i, Index is\n", Index);
        Status      = AsciiStringToUint64 (argv[Index + 1], FALSE, &StartAddress1);
//	      printf("\n%i, StartAddress1 is\n", StartAddress1);
        FirstRoundB = FALSE;
//	      printf("\n we get to here!\n");
//	      printf("\nStatus is %i\n", Status);
      } else {
//        printf("\nthe second round\n");
        Status = AsciiStringToUint64 (argv[Index + 1], FALSE, &StartAddress2);
      }
      if (Status = 0) {
        printf ("\nERROR: Bad start of address \"%s\"\n", argv[Index + 1]);
        return 1;
      }
      break;

    case 'S':
    case 's':
//    printf("\nSize specified!\n");
      if (FirstRoundS) {
        Status      = AsciiStringToUint64 (argv[Index + 1], FALSE, &FwVolSize1);
//	      printf("\n %i, FwVolSize1 is\n",  FwVolSize1);
        FirstRoundS = FALSE;
      } else {
        Status = AsciiStringToUint64 (argv[Index + 1], FALSE, &FwVolSize2);
      }

      if (Status != EFI_SUCCESS) {
        printf ("\nERROR: Bad size \"%s\"\n", argv[Index + 1]);
        return 1;
      }
      break;

    default:
      Usage ();
      printf ("ERROR: Unrecognized argument \"%s\".\n", argv[Index]);
      return 1;
      break;
    }
  }

  //
  // Call the GenVtfImage
  //
//  printf("\nStart to GenerateVtfImage!");
//  printf("\nStartAddress1 is %d", StartAddress1);
  printf("\nFwVolSize1 is %d", FwVolSize1);
//  printf("\nStartAddress2 is %d", StartAddress2);
  printf("\nFwVolSize2 is %d", FwVolSize2);
  Status = GenerateVtfImage (StartAddress1, FwVolSize1, StartAddress2, FwVolSize2, VtfFP);

  if (EFI_ERROR (Status)) {
    switch (Status) {

    case EFI_INVALID_PARAMETER:
      printf("\nWe come here!");
      printf ("\nERROR: Invalid parameter passed to GenVtfImage function .\n");
      break;

    case EFI_ABORTED:
      printf ("\nERROR: Error detected while creating the file image.\n");
      break;

    case EFI_OUT_OF_RESOURCES:
      printf ("\nERROR: GenVtfImage function could not allocate required resources.\n");
      break;

    case EFI_VOLUME_CORRUPTED:
      printf ("\nERROR: No base address was specified \n");
      break;

    default:
      printf ("\nERROR: GenVtfImage function returned unknown status %X.\n", Status);
      break;
    }
    return 2;
  }
  return 0;
}

EFI_STATUS
Generate32VtfImage (
IN  UINT64  BootFileStartAddress
  )
/*++

Routine Description:

  This is the main IA32 function which will be called from application.
  (Now this tool is not used for IA32 platform, if it will be used in future,
  the relative functions need to be updated, the updating can refer to IPF 
  functions)

Arguments:

  BootFileStartAddress   - Top Address of Boot File

Returns:
 
  The return value can be any of the values 
  returned by the calls to following functions:
      Get32VftRelatedInfoFromInfFile
      CreateVtfBuffer
      ProcessAndCreate32Vtf
      Update32FfsHeader
      WriteVtfBinary
  
--*/
{
  EFI_STATUS    Status;
  UINT32        VtfSize;
  CHAR8         OutFileName[FILE_NAME_SIZE];

  EFI_GUID      VtfNameGuid = EFI_IA32_BOOT_STRAP_GUID;

  Status = EFI_UNSUPPORTED;

  memset (OutFileName, 0, FILE_NAME_SIZE);

  sprintf (
    OutFileName, "%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x-%s",
    VtfNameGuid.Data1,
    VtfNameGuid.Data2,
    VtfNameGuid.Data3,
    VtfNameGuid.Data4[0],
    VtfNameGuid.Data4[1],
    VtfNameGuid.Data4[2],
    VtfNameGuid.Data4[3],
    VtfNameGuid.Data4[4],
    VtfNameGuid.Data4[5],
    VtfNameGuid.Data4[6],
    VtfNameGuid.Data4[7],
    VTF_OUTPUT_FILE
    );


  Status = Get32VtfRelatedInfoFromInfFile (VTF_INPUT_FILE);

  if (Status != EFI_SUCCESS) {
    printf ("\nERROR: Error in parsing input file");
    CleanUpMemory ();
    return Status;
  }

  if (GetTotal32VtfSize (&VtfSize) == EFI_SUCCESS) {
    Vtf1Buffer = malloc ((UINTN) VtfSize);
    if (Vtf1Buffer == NULL) {
      printf ("\nERROR: Not enough resource to create memory mapped file for Boot Strap File");
      CleanUpMemory ();
      return EFI_OUT_OF_RESOURCES;
    }
    memset (Vtf1Buffer, 0x00, (UINTN) VtfSize);
  } else {
    printf ("\nERROR: Could not get VTF size.");
    CleanUpMemory ();
    return EFI_ABORTED;
  }

  //
  //VTF must align properly
  //
  Vtf1LastStartAddress = BootFileStartAddress - VtfSize;
  Vtf1LastStartAddress = Vtf1LastStartAddress & -8;
  VtfSize          = (UINT32)BootFileStartAddress - (UINT32)Vtf1LastStartAddress;
  Vtf1LastStartAddress = VtfSize;
  BufferToTop      = (UINT32)BootFileStartAddress - VtfSize;

  Status = ProcessAndCreate32Vtf (VtfSize);

  if (Status != EFI_SUCCESS) {
    CleanUpMemory();
    return Status;
  }

  //
  // Write the FFS header
  //
  Status = Update32FfsHeader (VtfSize);

  if (Status != EFI_SUCCESS) {
    CleanUpMemory();
    return Status;
  }

  // 
  // Calculate the Start address of this VTF
  //
  Vtf1Buffer = (UINT8 *)Vtf1Buffer + Vtf1LastStartAddress;

  //
  // Update the VTF buffer into specified VTF binary file
  //
  Status = WriteVtfBinary (OutFileName, VtfSize - (UINT32)Vtf1LastStartAddress, FIRST_VTF);

  if (Status != EFI_SUCCESS) {
    CleanUpMemory();
    return Status;
  }

  Status = Write32SoftFit (IA32_SOFT_FIT, FileListHeadPtr);

  if (Status != EFI_SUCCESS) {
    CleanUpMemory();
    return Status;
  }
  
  CleanUpMemory ();
  printf ("\n");  

  return Status;
}

EFI_STATUS
GetTotal32VtfSize(
  IN  UINT32  *VtfSize 
  )
/*++

Routine Description:

  This function calculates total size for IA32 VTF which would be needed to create
  the buffer. This will be done using Passed Info link list and looking for the
  size of the components which belong to VTF. The addtional file header is accounted.

Arguments:

  VTFSize     - Pointer to the size of IA32 VTF 

Returns:

  EFI_ABORTED - Returned due to one of the following resons:
                (a) Error Opening File
  EFI_SUCCESS - The fuction completes successfully

--*/
{
  PARSED_VTF_INFO     *VtfInfo;
  FILE                *Fp;
  UINT32              Alignment;

  *VtfSize = 0;
  Alignment = 0;
  
  VtfInfo = FileListHeadPtr;

  while (VtfInfo != NULL) {
    if (VtfInfo->LocationType != SECOND_VTF) {

      if ( VtfInfo->Align ) {
        //
        // Create additional align to compensate for component boundary requirements
        //
        Alignment = 1 << VtfInfo->Align;
        *VtfSize += Alignment;
      }
      
      if (VtfInfo->PreferredSize) {
        *VtfSize += VtfInfo->CompSize;
      } else {
        Fp = fopen (VtfInfo->CompBinName,"r+b");

        if (Fp == NULL) {
          printf ("\nERROR: Error in opening file %s", VtfInfo->CompBinName);
          return EFI_ABORTED;
        }
        
        *VtfSize += _filelength (fileno (Fp));
        
        if (Fp) {
          fclose (Fp);
        }
      }    
    }
    VtfInfo = VtfInfo->NextVtfInfo;
  }

  //
  // Add file header space
  //
  *VtfSize += sizeof (EFI_FFS_FILE_HEADER);

  //
  // Create additional to IA32 Seccore section header
  //
  *VtfSize += sizeof (EFI_COMMON_SECTION_HEADER);

  return EFI_SUCCESS;
}

EFI_STATUS
ProcessAndCreate32Vtf (
  IN  UINT64  Size
  )
/*++

Routine Description:

  This function process the link list created during INF file parsing
  and create component in IA32 VTF
  
Arguments:

  Size   - Size of the Firmware Volume of which, this VTF belongs to.

Returns:
  
  EFI_UNSUPPORTED - Unknown component type
  EFI_SUCCESS     - The function completed successfully                 

--*/
{
  EFI_STATUS          Status;
  PARSED_VTF_INFO     *ParsedInfoPtr;

  Status = EFI_SUCCESS;

  ParsedInfoPtr = FileListHeadPtr;

  while (ParsedInfoPtr != NULL) {
    
    switch (ParsedInfoPtr->CompType) {

    case COMP_TYPE_SECCORE:
      Status = CreateAndUpdateSeccore (ParsedInfoPtr);
      break;

    default:
      //
      // Any other component type should be handled here. This will create the
      // image in specified VTF
      //
      Status = CreateAndUpdate32Component (ParsedInfoPtr);
      if (EFI_ERROR(Status)) {
        printf ("ERROR: Updating %s component.\n", ParsedInfoPtr->CompName);
      }
      break;
    }

    ParsedInfoPtr = ParsedInfoPtr->NextVtfInfo;
  }

  return Status;
}

EFI_STATUS
CreateAndUpdateSeccore (
  IN  PARSED_VTF_INFO   *VtfInfo
  )
/*++
  
Routine Description:

  This function reads the binary file for seccore and update them
  in IA32 VTF Buffer
  
Arguments:

  VtfInfo    - Pointer to Parsed Info
  
Returns:

  EFI_ABORTED           - Due to one of the following reasons:
                           (a)Error Opening File
                           (b)The PAL_A Size is more than specified size status
                              One of the values mentioned below returned from 
                              call to UpdateSymFile
  EFI_SUCCESS           - The function completed successfully.
  EFI_INVALID_PARAMETER - One of the input parameters was invalid.
  EFI_ABORTED           - An error occurred.UpdateSymFile
  EFI_OUT_OF_RESOURCES  - Memory allocation failed.
   
--*/
{
  UINT8                      *SecbinStartAddress;
  UINT8                      *SecfileStartAddress;
  UINT32                     FileSize;
  UINT64                     NumByteRead;
  UINT8                      *Buffer;
  FILE                       *Fp;
  UINT64                     TotalLength;
  EFI_COMMON_SECTION_HEADER  *SecHeader;

  Fp = fopen (VtfInfo->CompBinName, "r+b");

  if (Fp == NULL) {
    printf ("\nERROR: Opening file %s", VtfInfo->CompBinName);
    return EFI_ABORTED;
  }

  FileSize = _filelength (fileno (Fp));

  if (VtfInfo->PreferredSize) {
    if (FileSize > VtfInfo->CompSize) {
      printf("\nERROR: The Seccore Size is more than specified size");
      return EFI_ABORTED;
    }

    FileSize = VtfInfo->CompSize;
  }

  VtfInfo->CompSize = FileSize;

  Buffer = malloc ((UINTN) FileSize);
  if (Buffer == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }
  memset (Buffer, 0, (UINTN) FileSize);

  //
  // Read seccore in a buffer
  //
  NumByteRead = fread (Buffer, sizeof (UINT8), (UINTN) FileSize, Fp);
  fclose (Fp);

  SecfileStartAddress = (UINT8 *) Vtf1Buffer + Vtf1LastStartAddress - FileSize - sizeof (EFI_COMMON_SECTION_HEADER); 
  if (SecfileStartAddress == NULL) {
    return EFI_INVALID_PARAMETER;
  }

  SecbinStartAddress = SecfileStartAddress + sizeof (EFI_COMMON_SECTION_HEADER);

  VtfInfo->CompPreferredAddress = Vtf1LastStartAddress - FileSize + BufferToTop;

  //
  // write section header
  //
  memset (SecfileStartAddress, 0, sizeof (EFI_COMMON_SECTION_HEADER));
  SecHeader = (EFI_COMMON_SECTION_HEADER *) SecfileStartAddress;
  SecHeader->Type = EFI_SECTION_RAW;
  TotalLength     = sizeof (EFI_COMMON_SECTION_HEADER) + (UINT64) FileSize;
  memcpy (SecHeader->Size, &TotalLength, 3);

  //
  // write seccore
  //
  memcpy (SecbinStartAddress, Buffer, (UINTN) FileSize);

  if (Buffer) {
    free (Buffer);
  }

  Vtf1LastStartAddress = SecfileStartAddress - (UINT8 *) Vtf1Buffer;

  return EFI_SUCCESS;
}

EFI_STATUS
CreateAndUpdate32Component (
  IN  PARSED_VTF_INFO   *VtfInfo
  )
/*++
  
Routine Description:

  This function reads the binary file for each components. Add it at aligned address.
  
Arguments:

  VtfInfo    - Pointer to Parsed Info
  
Returns:

  EFI_SUCCESS              - The function completed successful
  EFI_ABORTED              - Aborted due to one of the many reasons like:
                              (a) Component Size greater than the specified size.
                              (b) Error opening files.
  EFI_INVALID_PARAMETER    - Value returned from call to UpdateEntryPoint()
  EFI_OUT_OF_RESOURCES     - Memory allocation failed.
  
--*/
{
  UINT64      CompStartAddress;
  UINT32      FileSize;
  UINT64      NumByteRead;
  UINT8       *Buffer;
  FILE        *Fp;
  UINT8       *LocalBufferPtrToWrite;
  UINT64      Alignment;

  Fp = fopen (VtfInfo->CompBinName, "r+b");

  if (Fp == NULL) {
    printf("\nERROR: Opening file %s", VtfInfo->CompBinName);
    return EFI_ABORTED;
  }

  FileSize = _filelength (fileno (Fp));

  if (VtfInfo->PreferredSize) {
    if (FileSize > VtfInfo->CompSize) {
      printf("\nERROR: The component size is more than specified size");
      return EFI_ABORTED;
    }
    FileSize = VtfInfo->CompSize;
  }
  VtfInfo->CompSize = FileSize;

  Buffer = malloc ((UINTN) FileSize);
  if (Buffer == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }
  memset (Buffer,0, (UINTN) FileSize);

  NumByteRead = fread (Buffer, sizeof (UINT8), (UINTN) FileSize, Fp);
  fclose (Fp);

  CompStartAddress = Vtf1LastStartAddress - FileSize + BufferToTop;

  if (VtfInfo->Align) {
    //
    // Create additional align to compensate for component boundary requirements
    //
    Alignment = 0 - (1 << VtfInfo->Align);
    CompStartAddress = CompStartAddress & Alignment;    
  }

  VtfInfo->CompPreferredAddress = CompStartAddress;

  //
  // write bin
  //
  LocalBufferPtrToWrite = (UINT8 *) Vtf1Buffer;
  Vtf1LastStartAddress  = CompStartAddress - BufferToTop;
  LocalBufferPtrToWrite += Vtf1LastStartAddress;
  memcpy (LocalBufferPtrToWrite, Buffer, (UINTN) FileSize);  
  Vtf1LastStartAddress = CompStartAddress - BufferToTop;

  //
  // Free the buffer
  //
  if (Buffer) {
    free (Buffer);
  }

  return EFI_SUCCESS;
}

EFI_STATUS
Update32FfsHeader(
  IN UINT32     VtfSize
  )
/*++

Routine Description:

  Update the Firmware Volume Buffer with requested buffer data

Arguments:

  VtfSize     - Size of the IA32 VTF

Returns:
  
  EFI_SUCCESS            - The function completed successfully
  EFI_INVALID_PARAMETER  - The Ffs File Header Pointer is NULL

--*/
{
  EFI_FFS_FILE_HEADER     *FileHeader;
  UINT32                  TotalVtfSize;
  EFI_GUID                EfiFirmwareVolumeTopFileGuid = EFI_FFS_VOLUME_TOP_FILE_GUID;

  
  //
  // Find the VTF file header location, the VTF file must be 8 bytes aligned
  //
  Vtf1LastStartAddress -= sizeof (EFI_FFS_FILE_HEADER);
  Vtf1LastStartAddress += BufferToTop;
  Vtf1LastStartAddress = Vtf1LastStartAddress & -8;
  Vtf1LastStartAddress -= BufferToTop;
  FileHeader = (EFI_FFS_FILE_HEADER*)((UINT8*)Vtf1Buffer + Vtf1LastStartAddress);

  if (FileHeader == NULL) {
    return EFI_INVALID_PARAMETER;
  }

  //
  // write header
  //
  memset (FileHeader, 0, sizeof(EFI_FFS_FILE_HEADER));
  memcpy (&FileHeader->Name, &EfiFirmwareVolumeTopFileGuid, sizeof (EFI_GUID));

  FileHeader->Type = EFI_FV_FILETYPE_FREEFORM;
  FileHeader->Attributes = FFS_ATTRIB_CHECKSUM;

  //
  // Now FileSize includes the EFI_FFS_FILE_HEADER
  //
  TotalVtfSize = VtfSize - (UINT32)Vtf1LastStartAddress;
  FileHeader->Size[0] = (UINT8) (TotalVtfSize & 0x000000FF);
  FileHeader->Size[1] = (UINT8) ((TotalVtfSize & 0x0000FF00) >> 8);
  FileHeader->Size[2] = (UINT8) ((TotalVtfSize & 0x00FF0000) >> 16);

  //
  // Fill in checksums and state, all three must be zero for the checksums.
  //
  FileHeader->IntegrityCheck.Checksum.Header = 0;
  FileHeader->IntegrityCheck.Checksum.File = 0;
  FileHeader->State = 0;
  FileHeader->IntegrityCheck.Checksum.Header = CalculateChecksum8 ((UINT8*) FileHeader, sizeof (EFI_FFS_FILE_HEADER));
  FileHeader->IntegrityCheck.Checksum.File = CalculateChecksum8 ((UINT8*) FileHeader, TotalVtfSize);
  FileHeader->State = EFI_FILE_HEADER_CONSTRUCTION | EFI_FILE_HEADER_VALID | EFI_FILE_DATA_VALID;

  return EFI_SUCCESS;
}

EFI_STATUS
Get32VtfRelatedInfoFromInfFile (
  IN  CHAR8 *FileName
  )
/*++
  
Routine Description:

  This function reads the input file, parse it and create a list of tokens
  which is parsed and used, to intialize the data related to IA32 VTF
  
Arguments:

  FileName  FileName which needed to be read to parse data

Returns:
   
  EFI_ABORTED            Error in opening file
  EFI_INVALID_PARAMETER  File doesn't contain any valid informations
  EFI_OUT_OF_RESOURCES   Malloc Failed
  EFI_SUCCESS            The function completed successfully 

--*/
{
  FILE          *Fp;
  UINTN         Index;
  EFI_STATUS    Status;
  
  Fp = fopen (FileName, "r");
  if (Fp == NULL) {
    printf ("\nERROR: Error in opening %s file\n", FileName);
    return EFI_ABORTED;
  }
  
  printf("\n%s", *FileName);
  ValidLineCount (Fp);
  
  if (ValidLineNum == 0) {
    printf ("\nERROR: File doesn't contain any valid informations");
    return EFI_INVALID_PARAMETER;
  }
  
  TokenStr = (CHAR8 **)malloc (sizeof (UINTN) * (2 * ValidLineNum + 1));

  if (TokenStr == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }
  memset (TokenStr, 0, (sizeof (UINTN) * (2 * ValidLineNum + 1)));
  OrgStrTokPtr = TokenStr;
  
  for (Index = 0; Index < (2 * ValidLineNum); Index++) {
    *TokenStr = (CHAR8 *)malloc (sizeof (CHAR8) * FILE_NAME_SIZE);

    if (*TokenStr == NULL) {
      free (OrgStrTokPtr);
      return EFI_OUT_OF_RESOURCES;
    }
    
    memset (*TokenStr, 0, FILE_NAME_SIZE);
//    free (*TokenStr);
    TokenStr++;
  }
  
  TokenStr = NULL;
  TokenStr = OrgStrTokPtr;
  fseek (Fp, 0L, SEEK_SET);
  
  Status = InitializeComps();

  if (Status != EFI_SUCCESS) {
    free (TokenStr);
    return Status;
  }
  ParseInputFile (Fp);
  Initialize32InFileInfo ();
  
  if (Fp) {
    fclose (Fp);
  }
  free (TokenStr);
  return EFI_SUCCESS;
}

VOID
Initialize32InFileInfo (
  VOID                     
  )
/*++

Routine Description:

  This function intializes the relevant global variable which is being
  used to store the information retrieved from IA32 INF file.

Arguments:

  NONE

Returns:

  NONE

--*/
{
  UINTN   SectionOptionFlag;
  UINTN   SectionCompFlag;

  SectionOptionFlag =0 ;
  SectionCompFlag = 0;  
  TokenStr = OrgStrTokPtr;
  while (*TokenStr != NULL) {
    if (strnicmp (*TokenStr, "[OPTIONS]", 9) == 0) {
      SectionOptionFlag = 1;
      SectionCompFlag = 0;
    }
    
    if (strnicmp (*TokenStr, "[COMPONENTS]", 12) == 0) {
      if (FileListPtr == NULL) {
        FileListPtr = FileListHeadPtr;
      }
      
      SectionCompFlag = 1;
      SectionOptionFlag = 0;
      TokenStr++;
    }
    
    if (SectionOptionFlag) {
      if (strnicmp (*TokenStr, "IA32_RST_BIN", 12) == 0) {
        *TokenStr++;
        strcpy (IA32BinFile, *TokenStr);
      }
    }
    
    if (SectionCompFlag) {
      if (strnicmp (*TokenStr, "COMP_NAME", 9) == 0) {
        TokenStr++;
        strcpy (FileListPtr->CompName, *TokenStr);
        TokenStr++;
        ParseAndUpdate32Components (FileListPtr);
      }
      
      if (*TokenStr != NULL) {
        FileListPtr->NextVtfInfo = malloc (sizeof (PARSED_VTF_INFO));
        if (FileListPtr->NextVtfInfo == NULL) {
          printf ("Error: Out of memory resources.\n");
          break;
        }
        FileListPtr = FileListPtr->NextVtfInfo;
        memset (FileListPtr, 0, sizeof(PARSED_VTF_INFO));
        FileListPtr->NextVtfInfo = NULL;
        continue;
      } else {
        break;
      }
    }
    
    TokenStr++;
  }
}

VOID 
ParseAndUpdate32Components (
  IN  PARSED_VTF_INFO   *VtfInfo
  )
/*++

Routine Description:

  This function intializes the relevant global variable which is being
  used to store the information retrieved from INF file.
  
Arguments:

  VtfInfo   - A pointer to the VTF Info Structure
  

Returns:

  None

--*/
{
  UINT64  StringValue;
  UINT64  AlignStringValue;

  while (*TokenStr != NULL && (strnicmp (*TokenStr, "COMP_NAME", 9) != 0)) {

    if (strnicmp (*TokenStr, "COMP_LOC", 8) == 0) {
      TokenStr++;
      if (strnicmp (*TokenStr, "B", 1) == 0) {
        VtfInfo->LocationType = FIRST_VTF;
      } else if (strnicmp (*TokenStr, "N", 1) == 0) {
        VtfInfo->LocationType = SECOND_VTF;
      } else {
        VtfInfo->LocationType = NONE;
        printf ("\nERROR: Unknown location for component %s", VtfInfo->CompName);
      }
    } else if (strnicmp (*TokenStr, "COMP_TYPE", 9) == 0) {
      TokenStr++;
      if (AsciiStringToUint64 (*TokenStr, FALSE, &StringValue) != EFI_SUCCESS) {
        printf ("\nERROR: Could not read a numeric value from \"%s\".", TokenStr); 
        return;
      }
      VtfInfo->CompType = (UINT8) StringValue;
    } else if (strnicmp (*TokenStr, "COMP_VER", 8) == 0) {
      TokenStr++;
      if (strnicmp (*TokenStr, "-", 1) == 0) {
        VtfInfo->VersionPresent = FALSE;
        VtfInfo->MajorVer = 0;
        VtfInfo->MinorVer = 0;
      } else {
        VtfInfo->VersionPresent = TRUE;
        ConvertVersionInfo (*TokenStr, &VtfInfo->MajorVer, &VtfInfo->MinorVer);
      }
    } else if (strnicmp (*TokenStr, "COMP_BIN", 8) == 0) {
      TokenStr++;
      strcpy (VtfInfo->CompBinName, *TokenStr);
    } else if (strnicmp (*TokenStr, "COMP_SYM", 8) == 0) {
      TokenStr++;
      strcpy (VtfInfo->CompSymName, *TokenStr);
    } else if (strnicmp (*TokenStr, "COMP_SIZE", 9) == 0) {
      TokenStr++;
      if (strnicmp (*TokenStr, "-", 1) == 0) {
        VtfInfo->PreferredSize = FALSE;
        VtfInfo->CompSize = 0;
      } else {
        VtfInfo->PreferredSize = TRUE;
        if (AsciiStringToUint64 (*TokenStr, FALSE, &StringValue) != EFI_SUCCESS) {
          printf ("\nERROR: Could not read a numeric value from \"%s\".", TokenStr); 
          return;
        }
        VtfInfo->CompSize = (UINTN) StringValue;
      }

    } else if (strnicmp (*TokenStr, "COMP_CS", 7) == 0) {
      TokenStr++;
      if (strnicmp (*TokenStr, "1", 1) == 0) {
        VtfInfo->CheckSumRequired = 1;
      } else if (strnicmp (*TokenStr, "0", 1) == 0) {
        VtfInfo->CheckSumRequired = 0;
      } else {
        printf ("\nERROR: Bad information in INF file about Checksum required field");
      }
    } else if (strnicmp (*TokenStr, "COMP_ALIGN", 10) == 0) {
      TokenStr++;
      if (AsciiStringToUint64 (*TokenStr, FALSE, &AlignStringValue) != EFI_SUCCESS) {
        printf ("\nERROR: Could not read a numeric value from \"%s\".", TokenStr); 
        return;
      }
      if (AlignStringValue >= 0) {
        VtfInfo->Align = (UINT32) AlignStringValue;
      } else {
        printf ("\nERROR: invalid align \"%s\".", AlignStringValue); 
        return;
      }
    }
    TokenStr++;
    if (*TokenStr == NULL) {
      break;
    }
  }
}

EFI_STATUS
Write32SoftFit(
  IN CHAR8              *FileName,
  IN PARSED_VTF_INFO    *VtfInfo
  )
/*++

Routine Description:

  Write IA32 Firmware Volume component address from memory to a file.
  
Arguments:

  FileName      Output File Name which needed to be created/
  VtfInfo       Parsed info link
  
Returns:

  EFI_ABORTED  - Returned due to one of the following resons:
                  (a) Error Opening File
                  (b) Failing to copy buffers
  EFI_SUCCESS  - The function completes successfully

--*/
{
  FILE    *Fp;

  Fp = fopen (FileName, "w+t");
  if (Fp == NULL) {
    printf ("Error in opening file %s\n", FileName);
    return EFI_ABORTED;
  }

  while (VtfInfo != NULL) {
    if (strlen (VtfInfo->CompName) != 0) {
      fprintf (Fp, "\n%s\n", VtfInfo->CompName);
    } else {
      fprintf (Fp, "\n%s\n", "Name not available");    
    }
    
    fprintf (Fp, "%d\n", VtfInfo->CompPreferredAddress);
    fprintf (Fp, "%d\n", VtfInfo->CompSize);
    fprintf (Fp, "%d\n", VtfInfo->Align);
    
    VtfInfo = VtfInfo->NextVtfInfo;
  }

  if (Fp) {
    fclose (Fp);
  }

  return EFI_SUCCESS;
}