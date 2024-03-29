/** @file

Copyright (c)  1999-2008 Intel Corporation. All rights reserved
This program and the accompanying materials are licensed and made available 
under the terms and conditions of the BSD License which accompanies this 
distribution.  The full text of the license may be found at
http://opensource.org/licenses/bsd-license.php

THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.

Module Name:

  EfiRom.c
  
Abstract:

  Utility program to create an EFI option ROM image from binary and 
  EFI PE32 files.

**/

#include "EfiRom.h"

main (
  int   Argc,
  char  *Argv[]
  )
/*++

Routine Description:
  
  Given an EFI image filename, create a ROM-able image by creating an option 
  ROM header and PCI data structure, filling them in, and then writing the
  option ROM header + PCI data structure + EFI image out to the output file.

Arguments:

  Argc            - standard C main() argument count

  Argv            - standard C main() argument list

Returns:

  0             success
  non-zero      otherwise

--*/
{
  INT8      *Ext;
  FILE      *FptrOut;
  UINT32    Status;
  FILE_LIST *FList;
  UINT32    TotalSize;
  UINT32    Size;
  CHAR8     *Ptr0;

  SetUtilityName(UTILITY_NAME);

  Status  = STATUS_SUCCESS;
  FptrOut = NULL;

  //
  // Parse the command line arguments
  //
  if (ParseCommandLine (Argc, Argv, &mOptions)) {
    return STATUS_ERROR;
  }

  if (mOptions.Quiet) {
    SetPrintLevel(40);
  } else if (mOptions.Verbose) {
    SetPrintLevel(15);
  } else if (mOptions.Debug) {
    SetPrintLevel(DebugLevel);
  }
  
  if (mOptions.Verbose) {
    VerboseMsg("%s tool start.\n", UTILITY_NAME);
  }
  
  if (mOptions.FileList == NULL) {
    Error (NULL, 0, 1002, "No input file", NULL);
    goto BailOut;
  }
  //
  // If dumping an image, then do that and quit
  //
  if (mOptions.DumpOption == 1) {
    for (FList = mOptions.FileList; FList != NULL; FList = FList->Next) {
      if ((Ptr0 = strstr ((CONST CHAR8 *)FList->FileName, DEFAULT_OUTPUT_EXTENSION)) != NULL) {
        DumpImage (mOptions.FileList);
        goto BailOut;
      } else {
        Error (NULL, 0, 1002, "No PciRom input file", "No *.rom input file");
        goto BailOut;
      }
    }
  }
  //
  // Determine the output filename. Either what they specified on
  // the command line, or the first input filename with a different extension.
  //
  if (!mOptions.OutFileName[0]) {
    strcpy (mOptions.OutFileName, mOptions.FileList->FileName);
    //
    // Find the last . on the line and replace the filename extension with
    // the default
    //
    for (Ext = mOptions.OutFileName + strlen (mOptions.OutFileName) - 1;
         (Ext >= mOptions.OutFileName) && (*Ext != '.') && (*Ext != '\\');
         Ext--
        )
      ;
    //
    // If dot here, then insert extension here, otherwise append
    //
    if (*Ext != '.') {
      Ext = mOptions.OutFileName + strlen (mOptions.OutFileName);
    }

    strcpy (Ext, DEFAULT_OUTPUT_EXTENSION);
  }
  //
  // Make sure we don't have the same filename for input and output files
  //
  for (FList = mOptions.FileList; FList != NULL; FList = FList->Next) {
    if (stricmp (mOptions.OutFileName, FList->FileName) == 0) {
      Status = STATUS_ERROR;
      Error (NULL, 0, 1002, "Invalid input paramter", "Input and output file names must be different - %s = %s.", FList->FileName, mOptions.OutFileName);
      goto BailOut;
    }
  }
  //
  // Now open our output file
  //
  if ((FptrOut = fopen (mOptions.OutFileName, "wb")) == NULL) {
    Error (stdout, 0, 0001, "Error opening file", mOptions.OutFileName);
    goto BailOut;
  }
  //
  // Process all our files
  //
  TotalSize = 0;
  for (FList = mOptions.FileList; FList != NULL; FList = FList->Next) {
    Size = 0;
    if ((FList->FileFlags & FILE_FLAG_EFI) != 0) {
      if (mOptions.Verbose) {
        VerboseMsg("Processing EFI file    %s\n", FList->FileName);
      }

      Status = ProcessEfiFile (FptrOut, FList, mOptions.VendId, mOptions.DevId, &Size);
    } else if ((FList->FileFlags & FILE_FLAG_BINARY) !=0 ) {
      if (mOptions.Verbose) {
        VerboseMsg("Processing binary file %s\n", FList->FileName);
      }

      Status = ProcessBinFile (FptrOut, FList, &Size);
    } else {
      Error (stdout, 0, 2000, "Invalid parameter", "File type not specified, it must be either an EFI or binary file: %s.", FList->FileName);
      Status = STATUS_ERROR;
    }

    if (mOptions.Verbose) {
      VerboseMsg("  Output size = 0x%X\n", Size);
    }

    if (Status != STATUS_SUCCESS) {
      break;
    }

    TotalSize += Size;
  }
  //
  // Check total size
  //
  if (TotalSize > MAX_OPTION_ROM_SIZE) {
    Error (NULL, 0, 2000, "Invalid paramter", "Option ROM image size exceeds limit of 0x%X bytes.", MAX_OPTION_ROM_SIZE);
    Status = STATUS_ERROR;
  }

BailOut:
  if (Status == STATUS_SUCCESS) {
    if (FptrOut != NULL) {
      fclose (FptrOut);
    }
    //
    // Clean up our file list
    //
    while (mOptions.FileList != NULL) {
      FList = mOptions.FileList->Next;
      free (mOptions.FileList);
      mOptions.FileList = FList;
    }
  }

  if (mOptions.Verbose) {
    VerboseMsg("%s tool done with return code is 0x%x.\n", UTILITY_NAME, GetUtilityStatus ());
  }

  return GetUtilityStatus (); 
}

static
int
ProcessBinFile (
  FILE      *OutFptr,
  FILE_LIST *InFile,
  UINT32    *Size
  )
/*++

Routine Description:
  
  Process a binary input file.

Arguments:

  OutFptr     - file pointer to output binary ROM image file we're creating
  InFile      - structure contains information on the binary file to process
  Size        - pointer to where to return the size added to the output file

Returns:

  0 - successful

--*/
{
  FILE                      *InFptr;
  UINT32                    TotalSize;
  UINT32                    FileSize;
  UINT8                     *Buffer;
  UINT32                    Status;
  PCI_EXPANSION_ROM_HEADER  *RomHdr;
  PCI_DATA_STRUCTURE        *PciDs23;
  PCI_3_0_DATA_STRUCTURE    *PciDs30;
  UINT32                    Index;
  UINT8                     ByteCheckSum;
 

  Status = STATUS_SUCCESS;

  //
  // Try to open the input file
  //
  if ((InFptr = fopen (InFile->FileName, "rb")) == NULL) {
    Error (NULL, 0, 0001, "Error opening file", InFile->FileName);
    return STATUS_ERROR;
  }
  //
  // Seek to the end of the input file and get the file size. Then allocate
  // a buffer to read it in to.
  //
  fseek (InFptr, 0, SEEK_END);
  FileSize = ftell (InFptr);
  if (mOptions.Verbose) {
    VerboseMsg("  File size   = 0x%X\n", FileSize);
  }

  fseek (InFptr, 0, SEEK_SET);
  Buffer = (INT8 *) malloc (FileSize);
  if (Buffer == NULL) {
    Error (NULL, 0, 4003, "Resource", "memory cannot be allocated!", NULL);
    Status = STATUS_ERROR;
    goto BailOut;
  }

  if (fread (Buffer, FileSize, 1, InFptr) != 1) {
    Error (NULL, 0, 2000, "Invalid", "Failed to read all bytes from input file.");
    Status = STATUS_ERROR;
    goto BailOut;
  }
  //
  // Total size must be an even multiple of 512 bytes, and can't exceed
  // the option ROM image size.
  //
  TotalSize = FileSize;
  if (TotalSize & 0x1FF) {
    TotalSize = (TotalSize + 0x200) &~0x1ff;
  }

  if (TotalSize > MAX_OPTION_ROM_SIZE) {
    Error (NULL, 0, 3001, "Invalid", "Option ROM image %s size exceeds limit of 0x%X bytes.", InFile->FileName, MAX_OPTION_ROM_SIZE);
    Status = STATUS_ERROR;
    goto BailOut;
  }
  //
  // Return the size to the caller so they can keep track of the running total.
  //
  *Size = TotalSize;

  //
  // Crude check to make sure it's a legitimate ROM image
  //
  RomHdr = (PCI_EXPANSION_ROM_HEADER *) Buffer;
  if (RomHdr->Signature != PCI_EXPANSION_ROM_HEADER_SIGNATURE) {
    Error (NULL, 0, 2000, "Invalid parameter", "ROM image file has an invalid ROM signature.");
    Status = STATUS_ERROR;
    goto BailOut;
  }
  //
  // Make sure the pointer to the PCI data structure is within the size of the image.
  // Then check it for valid signature.
  //
  if ((RomHdr->PcirOffset > FileSize) || (RomHdr->PcirOffset == 0)) {
    Error (NULL, 0, 2000, "Invalid parameter", "Invalid PCI data structure offset.");
    Status = STATUS_ERROR;
    goto BailOut;
  }

  //
  // Check the header is conform to PCI2.3 or PCI3.0
  //
  if (mOptions.Pci23 == 1) {
    PciDs23 = (PCI_DATA_STRUCTURE *) (Buffer + RomHdr->PcirOffset);
    if (PciDs23->Signature != PCI_DATA_STRUCTURE_SIGNATURE) {
      Error (NULL, 0, 2000, "Invalid parameter", "PCI data structure has an invalid signature.");
      Status = STATUS_ERROR;
      goto BailOut;
    }
  } else {
    //
    // Default setting is PCI3.0 header
    //
    PciDs30 = (PCI_3_0_DATA_STRUCTURE *)(Buffer + RomHdr->PcirOffset);
    if (PciDs30->Signature != PCI_DATA_STRUCTURE_SIGNATURE) {
      Error (NULL, 0, 2000, "Invalid parameter", "PCI data structure has an invalid signature.");
      Status = STATUS_ERROR;
      goto BailOut;
    }
  }

  
  //
  // If this is the last image, then set the LAST bit unless requested not
  // to via the command-line -n argument. Otherwise, make sure you clear it.
  //
  if ((InFile->Next == NULL) && (mOptions.NoLast == 0)) {
    if (mOptions.Pci23 == 1) {
      PciDs23->Indicator = INDICATOR_LAST;
    } else {
      PciDs30->Indicator = INDICATOR_LAST;
		}
  } else {
    if (mOptions.Pci23 == 1) {
      PciDs23->Indicator = 0;
    } else {
      PciDs30->Indicator = 0;
		}
  }

  ByteCheckSum = 0;
  for (Index = 0; Index < FileSize - 1; Index++) {
    ByteCheckSum = (UINT8) (ByteCheckSum + Buffer[Index]);
  }

  Buffer[FileSize - 1] = (UINT8) ((~ByteCheckSum) + 1);
  if (mOptions.Verbose) {
    VerboseMsg("  Checksum = %02x\n\n", (UINT32) Buffer[FileSize - 1]);
  }

  //
  // Now copy the input file contents out to the output file
  //
  if (fwrite (Buffer, FileSize, 1, OutFptr) != 1) {
    Error (NULL, 0, 0005, "Failed to write all file bytes to output file.");
    Status = STATUS_ERROR;
    goto BailOut;
  }

  TotalSize -= FileSize;
  //
  // Pad the rest of the image to make it a multiple of 512 bytes
  //
  while (TotalSize > 0) {
    putc (~0, OutFptr);
    TotalSize--;
  }

BailOut:
  if (InFptr != NULL) {
    fclose (InFptr);
  }

  if (Buffer != NULL) {
    free (Buffer);
  }
  //
  // Print the file name if errors occurred
  //
  if (Status != STATUS_SUCCESS) {
    Error (NULL, 0, 0003, "Error", "Error parsing file: %s", InFile->FileName);
  }

  return Status;
}

static
int
ProcessEfiFile (
  FILE      *OutFptr,
  FILE_LIST *InFile,
  UINT16    VendId,
  UINT16    DevId,
  UINT32    *Size
  )
/*++

Routine Description:
  
  Process a PE32 EFI file.

Arguments:

  OutFptr     - file pointer to output binary ROM image file we're creating
  InFile      - structure contains information on the PE32 file to process
  VendId      - vendor ID as required in the option ROM header
  DevId       - device ID as required in the option ROM header
  Size        - pointer to where to return the size added to the output file

Returns:

  0 - successful

--*/
{
  UINT32                        Status;
  FILE                          *InFptr;
  EFI_PCI_EXPANSION_ROM_HEADER  RomHdr;
  PCI_DATA_STRUCTURE            PciDs23;
  PCI_3_0_DATA_STRUCTURE        PciDs30;
  UINT32                        FileSize;
  UINT32                        CompressedFileSize;
  UINT8                         *Buffer;
  UINT8                         *CompressedBuffer;
  UINT8                         *TempBufferPtr;
  UINT32                        TotalSize;
  UINT32                        HeaderSize;
  UINT16                        MachineType;
  UINT16                        SubSystem;
  UINT32                        HeaderPadBytes;

  //
  // Try to open the input file
  //
  if ((InFptr = fopen (InFile->FileName, "rb")) == NULL) {
    Error (NULL, 0, 0001, "Open file error", "Error opening file: %s", InFile->FileName);
    return STATUS_ERROR;
  }
  //
  // Initialize our buffer pointers to null.
  //
  Buffer            = NULL;
  CompressedBuffer  = NULL;

  //
  // Double-check the file to make sure it's what we expect it to be
  //
  Status = CheckPE32File (InFptr, &MachineType, &SubSystem);
  if (Status != STATUS_SUCCESS) {
    goto BailOut;
  }
  //
  // Seek to the end of the input file and get the file size
  //
  fseek (InFptr, 0, SEEK_END);
  FileSize = ftell (InFptr);

  //
  // Get the size of the headers we're going to put in front of the image. The
  // EFI header must be aligned on a 4-byte boundary, so pad accordingly.
  //
  if (sizeof (RomHdr) & 0x03) {
    HeaderPadBytes = 4 - (sizeof (RomHdr) & 0x03);
  } else {
    HeaderPadBytes = 0;
  }
  
  //
  // For Pci3.0 to use the different data structure.
  //
  if (mOptions.Pci23 == 1) {
    HeaderSize = sizeof (PCI_DATA_STRUCTURE) + HeaderPadBytes + sizeof (EFI_PCI_EXPANSION_ROM_HEADER);
  } else {
    HeaderSize = sizeof (PCI_3_0_DATA_STRUCTURE) + HeaderPadBytes + sizeof (EFI_PCI_EXPANSION_ROM_HEADER);
  }

  if (mOptions.Verbose) {
    VerboseMsg("  File size   = 0x%X\n", FileSize);
  }
  //
  // Allocate memory for the entire file (in case we have to compress), then
  // seek back to the beginning of the file and read it into our buffer.
  //
  Buffer = (INT8 *) malloc (FileSize);
  if (Buffer == NULL) {
    Error (NULL, 0, 4001, "Resource", "memory cannot be allocated!");
    Status = STATUS_ERROR;
    goto BailOut;
  }

  fseek (InFptr, 0, SEEK_SET);
  if (fread (Buffer, FileSize, 1, InFptr) != 1) {
    Error (NULL, 0, 0004, "Error reading file", InFptr);
    Status = STATUS_ERROR;
    goto BailOut;
  }
  //
  // Now determine the size of the final output file. It's either the header size
  // plus the file's size, or the header size plus the compressed file size.
  //
  if ((InFile->FileFlags & FILE_FLAG_COMPRESS) != 0) {
    //
    // Allocate a buffer into which we can compress the image, compress it,
    // and use that size as the new size.
    //
    CompressedBuffer = (INT8 *) malloc (FileSize);
    if (CompressedBuffer == NULL) {
      Error (NULL, 0, 4001, "Resource", "memory cannot be allocated!");
      Status = STATUS_ERROR;
      goto BailOut;
    }

    CompressedFileSize  = FileSize;
    Status              = EfiCompress (Buffer, FileSize, CompressedBuffer, &CompressedFileSize);
    if (Status != STATUS_SUCCESS) {
      Error (NULL, 0, 0007, "Error compressing file!");
      goto BailOut;
    }
    //
    // Now compute the size, then swap buffer pointers.
    //
    if (mOptions.Verbose) {
      VerboseMsg("  Comp size   = 0x%X\n", CompressedFileSize);
    }

    TotalSize         = CompressedFileSize + HeaderSize;
    FileSize          = CompressedFileSize;
    TempBufferPtr     = Buffer;
    Buffer            = CompressedBuffer;
    CompressedBuffer  = TempBufferPtr;
  } else {
    TotalSize = FileSize + HeaderSize;
  }
  //
  // Total size must be an even multiple of 512 bytes
  //
  if (TotalSize & 0x1FF) {
    TotalSize = (TotalSize + 0x200) &~0x1ff;
  }
  //
  // Check size
  //
  if (TotalSize > MAX_OPTION_ROM_SIZE) {
    Error (NULL, 0, 2000, "Invalid", "Option ROM image %s size exceeds limit of 0x%X bytes.", InFile->FileName, MAX_OPTION_ROM_SIZE);	
    Status = STATUS_ERROR;
    goto BailOut;
  }
  //
  // Return the size to the caller so they can keep track of the running total.
  //
  *Size = TotalSize;

  //
  // Now fill in the ROM header. These values come from chapter 18 of the
  // EFI 1.02 specification.
  //
  memset (&RomHdr, 0, sizeof (RomHdr));
  RomHdr.Signature            = PCI_EXPANSION_ROM_HEADER_SIGNATURE;
  RomHdr.InitializationSize   = (UINT16) (TotalSize / 512);
  RomHdr.EfiSignature         = EFI_PCI_EXPANSION_ROM_HEADER_EFISIGNATURE;
  RomHdr.EfiSubsystem         = SubSystem;
  RomHdr.EfiMachineType       = MachineType;
  RomHdr.EfiImageHeaderOffset = (UINT16) HeaderSize;
  RomHdr.PcirOffset           = (UINT16) (sizeof (RomHdr) + HeaderPadBytes);
  //
  // Set image as compressed or not
  //
  if (InFile->FileFlags & FILE_FLAG_COMPRESS) {
    RomHdr.CompressionType = EFI_PCI_EXPANSION_ROM_HEADER_COMPRESSED;
  }
  //
  // Fill in the PCI data structure
  //
  if (mOptions.Pci23 == 1) {
    memset (&PciDs23, 0, sizeof (PCI_DATA_STRUCTURE));
  } else {
    memset (&PciDs30, 0, sizeof (PCI_3_0_DATA_STRUCTURE));
  }

  if (mOptions.Pci23 == 1) {
    PciDs23.Signature = PCI_DATA_STRUCTURE_SIGNATURE;
    PciDs23.VendorId  = VendId;
    PciDs23.DeviceId  = DevId;
    PciDs23.Length    = (UINT16) sizeof (PCI_DATA_STRUCTURE);
    PciDs23.Revision  = 0;
    //
    // Class code and code revision from the command line (optional)
    //
    PciDs23.ClassCode[0]  = (UINT8) InFile->ClassCode;
    PciDs23.ClassCode[1]  = (UINT8) (InFile->ClassCode >> 8);
    PciDs23.ClassCode[2]  = (UINT8) (InFile->ClassCode >> 16);
    PciDs23.ImageLength   = RomHdr.InitializationSize;
    PciDs23.CodeRevision  = InFile->CodeRevision;
    PciDs23.CodeType      = PCI_CODE_TYPE_EFI_IMAGE;
  } else {
    PciDs30.Signature = PCI_DATA_STRUCTURE_SIGNATURE;
    PciDs30.VendorId  = VendId;
    PciDs30.DeviceId  = DevId;
    PciDs30.DeviceListOffset = 0; // to be fixed
    PciDs30.Length    = (UINT16) sizeof (PCI_3_0_DATA_STRUCTURE);
    PciDs30.Revision  = 0;
    //
    // Class code and code revision from the command line (optional)
    //
    PciDs30.ClassCode[0]  = (UINT8) InFile->ClassCode;
    PciDs30.ClassCode[1]  = (UINT8) (InFile->ClassCode >> 8);
    PciDs30.ClassCode[2]  = (UINT8) (InFile->ClassCode >> 16);
    PciDs30.ImageLength   = RomHdr.InitializationSize;
    PciDs30.CodeRevision  = InFile->CodeRevision;
    PciDs30.CodeType      = PCI_CODE_TYPE_EFI_IMAGE;
    PciDs30.MaxRuntimeImageLength = 0; // to be fixed
    PciDs30.ConfigUtilityCodeHeaderOffset = 0; // to be fixed
    PciDs30.DMTFCLPEntryPointOffset = 0; // to be fixed
  }
  //
  // If this is the last image, then set the LAST bit unless requested not
  // to via the command-line -n argument.
  //
  if ((InFile->Next == NULL) && (mOptions.NoLast == 0)) {
    if (mOptions.Pci23 == 1) {
      PciDs23.Indicator = INDICATOR_LAST;
	  } else {
    PciDs30.Indicator = INDICATOR_LAST;}
  } else {
    if (mOptions.Pci23 == 1) {
      PciDs23.Indicator = 0;
	} else {
      PciDs30.Indicator = 0;
    }
  }
  //
  // Write the ROM header to the output file
  //
  if (fwrite (&RomHdr, sizeof (RomHdr), 1, OutFptr) != 1) {
    Error (NULL, 0, 0002, "Failed to write ROM header to output file!");
    Status = STATUS_ERROR;
    goto BailOut;
  }

  //
  // Write pad bytes to align the PciDs
  //
  while (HeaderPadBytes > 0) {
    if (putc (0, OutFptr) == EOF) {
      Error (NULL, 0, 0002, "Failed to write ROM header pad bytes to output file!");
      Status = STATUS_ERROR;
      goto BailOut;
    }

    HeaderPadBytes--;
  }
  //
  // Write the PCI data structure header to the output file
  //
  if (mOptions.Pci23 == 1) {
    if (fwrite (&PciDs23, sizeof (PciDs23), 1, OutFptr) != 1) {
      Error (NULL, 0, 0002, "Failed to write PCI ROM header to output file!");
      Status = STATUS_ERROR;
      goto BailOut;
    } 
  } else {
    if (fwrite (&PciDs30, sizeof (PciDs30), 1, OutFptr) != 1) {
      Error (NULL, 0, 0002, "Failed to write PCI ROM header to output file!");
      Status = STATUS_ERROR;
      goto BailOut;
    } 
  }
  //
  // Keep track of how many bytes left to write
  //
  TotalSize -= HeaderSize;

  //
  // Now dump the input file's contents to the output file
  //
  if (fwrite (Buffer, FileSize, 1, OutFptr) != 1) {
    Error (NULL, 0, 0002, "Failed to write all file bytes to output file!");
    Status = STATUS_ERROR;
    goto BailOut;
  }

  TotalSize -= FileSize;
  //
  // Pad the rest of the image to make it a multiple of 512 bytes
  //
  while (TotalSize > 0) {
    if (putc (~0, OutFptr) == EOF) {
      Error (NULL, 0, 2000, "Failed to write trailing pad bytes output file!");
      Status = STATUS_ERROR;
      goto BailOut;
    }

    TotalSize--;
  }

BailOut:
  if (InFptr != NULL) {
    fclose (InFptr);
  }
  //
  // Free up our buffers
  //
  if (Buffer != NULL) {
    free (Buffer);
  }

  if (CompressedBuffer != NULL) {
    free (CompressedBuffer);
  }
  //
  // Print the file name if errors occurred
  //
  if (Status != STATUS_SUCCESS) {
    Error (NULL, 0, 0003, "Error parsing", "Error parsing file: %s", InFile->FileName);
  }

  return Status;
}

static
int
CheckPE32File (
  FILE      *Fptr,
  UINT16    *MachineType,
  UINT16    *SubSystem
  )
/*++

Routine Description:
  
  Given a file pointer to a supposed PE32 image file, verify that it is indeed a
  PE32 image file, and then return the machine type in the supplied pointer.

Arguments:

  Fptr          File pointer to the already-opened PE32 file
  MachineType   Location to stuff the machine type of the PE32 file. This is needed
                because the image may be Itanium-based, IA32, or EBC.

Returns:

  0             success
  non-zero      otherwise

--*/
{
  EFI_IMAGE_DOS_HEADER      DosHeader;
  EFI_IMAGE_FILE_HEADER     FileHdr;
  EFI_IMAGE_OPTIONAL_HEADER OptionalHdr;
  UINT32                    PESig;

  //
  // Position to the start of the file
  //
  fseek (Fptr, 0, SEEK_SET);

  //
  // Read the DOS header
  //
  if (fread (&DosHeader, sizeof (DosHeader), 1, Fptr) != 1) {
    Error (NULL, 0, 0004, "Failed to read the DOS stub from the input file!");
    return STATUS_ERROR;
  }
  //
  // Check the magic number (0x5A4D)
  //
  if (DosHeader.e_magic != EFI_IMAGE_DOS_SIGNATURE) {
    Error (NULL, 0, 2000, "Invalid parameter", "Input file does not appear to be a PE32 image (magic number)!");
    return STATUS_ERROR;
  }
  //
  // Position into the file and check the PE signature
  //
  fseek (Fptr, (long) DosHeader.e_lfanew, SEEK_SET);
  if (fread (&PESig, sizeof (PESig), 1, Fptr) != 1) {
    Error (NULL, 0, 0004, "Failed to read PE signature bytes from input file!");
    return STATUS_ERROR;
  }
  //
  // Check the PE signature in the header "PE\0\0"
  //
  if (PESig != EFI_IMAGE_NT_SIGNATURE) {
    Error (NULL, 0, 2000, "Invalid parameter", "Input file does not appear to be a PE32 image (signature)!");
    return STATUS_ERROR;
  }
  //
  // Read the file header and stuff their MachineType
  //
  if (fread (&FileHdr, sizeof (FileHdr), 1, Fptr) != 1) {
    Error (NULL, 0, 0004, "Failed to read PE file header from input file!");
    return STATUS_ERROR;
  }

  memcpy ((char *) MachineType, &FileHdr.Machine, 2);

  //
  // Read the optional header so we can get the subsystem
  //
  if (fread (&OptionalHdr, sizeof (OptionalHdr), 1, Fptr) != 1) {
    Error (NULL, 0, 0004, "Failed to read COFF optional header from input file!");
    return STATUS_ERROR;
  }

  *SubSystem = OptionalHdr.Subsystem;
  if (mOptions.Verbose) {
    VerboseMsg("  Got subsystem = 0x%X from image\n", (int) *SubSystem);
  }
  //
  // Good to go
  //
  return STATUS_SUCCESS;
}

static
int
ParseCommandLine (
  int         Argc,
  char        *Argv[],
  OPTIONS     *Options
  )
/*++

Routine Description:
  
  Given the Argc/Argv program arguments, and a pointer to an options structure,
  parse the command-line options and check their validity.


Arguments:

  Argc            - standard C main() argument count
  Argv[]          - standard C main() argument list
  Options         - pointer to a structure to store the options in

Returns:

  STATUS_SUCCESS    success
  non-zero          otherwise

--*/
{
  FILE_LIST *FileList;

  FILE_LIST *PrevFileList;
  UINT32    FileFlags;
  UINT32    ClassCode;
  UINT32    CodeRevision;
  EFI_STATUS Status;

  FileFlags = 0;

  //
  // Clear out the options
  //
  memset ((char *) Options, 0, sizeof (OPTIONS));

  //
  // To avoid compile warnings
  //
  FileList                = PrevFileList = NULL;

  ClassCode               = 0;
  CodeRevision            = 0;
  //
  // Skip over the program name
  //
  Argc--;
  Argv++;

  //
  // If no arguments, assume they want usage info
  //
  if (Argc == 0) {
    Usage ();
    return STATUS_ERROR;
  }
  
  if ((strcmp(Argv[0], "-h") == 0) || (strcmp(Argv[0], "--help") == 0) ||
      (strcmp(Argv[0], "-?") == 0) || (strcmp(Argv[0], "/?") == 0)) {
    Usage();
    return STATUS_ERROR;
  }
  
  if ((strcmp(Argv[0], "--version") == 0)) {
    Version();
    return STATUS_ERROR;
  }

  //
  // Process until no more arguments
  //
  while (Argc > 0) {
    if ((Argv[0][0] == '-') || (Argv[0][0] == '/')) {
      //
      // To simplify string comparisons, replace slashes with dashes
      //
      Argv[0][0] = '-';
      
      //
      // Vendor ID specified with -f
      //
      if (stricmp (Argv[0], "-f") == 0) {
        //
        // Make sure there's another parameter
        //
        if (Argc > 1) {
          Options->VendId       = (UINT16) strtol (Argv[1], NULL, 16);
          Options->VendIdValid  = 1;
        } else {
	        Error (NULL, 0, 2000, "Invalid parameter", "Missing Vendor ID with %s!", Argv[0]);
          Usage ();
          return STATUS_ERROR;
        }

        Argv++;
        Argc--;
      } else if (stricmp (Argv[0], "-i") == 0) {
        //
        // Device ID specified with -i
        // Make sure there's another parameter
        //
        //printf("\nDevice id specified!\n");
        if (Argc > 1) {
          Options->DevId      = (UINT16) strtol (Argv[1], NULL, 16);
          Options->DevIdValid = 1;
        } else {
          Error (NULL, 0, 2000, "Invalid parameter", "Missing Device ID with %s!", Argv[0]);
          Usage ();
          return STATUS_ERROR;
        }

        Argv++;
        Argc--;
      } else if ((stricmp (Argv[0], "-o") == 0) || (stricmp (Argv[0], "--output") == 0)) {
        //
        // Output filename specified with -o
        // Make sure there's another parameter
        //
        if (Argc > 1) {
          strcpy (Options->OutFileName, Argv[1]);
        } else {
          Error (NULL, 0, 2000, "Invalid parameter", "Missing output file name with %s!", Argv[0]);
          Usage ();
          return STATUS_ERROR;
        }

        Argv++;
        Argc--;
      } else if ((stricmp (Argv[0], "-h") == 0) || (strcmp (Argv[0], "-?") == 0)) {
        //
        // Help option
        //
        Usage ();
        return STATUS_ERROR;
      } else if (stricmp (Argv[0], "-b") == 0) {
        //
        // Specify binary files with -b
        //
        FileFlags = FILE_FLAG_BINARY;
      } else if ((stricmp (Argv[0], "-e") == 0) || (stricmp (Argv[0], "-ec") == 0)) {
        //
        // Specify EFI files with -e. Specify EFI-compressed with -c.
        //
        FileFlags = FILE_FLAG_EFI;
        if ((Argv[0][2] == 'c') || (Argv[0][2] == 'C')) {
          FileFlags |= FILE_FLAG_COMPRESS;
        }
        //
        // Specify not to set the LAST bit in the last file with -n
        //
      } else if (stricmp (Argv[0], "-n") == 0) {
        Options->NoLast = 1;
      } else if (((stricmp (Argv[0], "-v") == 0)) || ((stricmp (Argv[0], "--verbose") == 0))) {
        //
        // -v for verbose
        //
        Options->Verbose = 1;
      } else if (stricmp (Argv[0], "--debug") == 0) {
        Argv++;
        Status = AsciiStringToUint64(Argv[0], FALSE, &DebugLevel);
        if (DebugLevel > 9 || DebugLevel < 0) {
          Error (NULL, 0, 2000, "Invalid parameter", "Unrecognized parameter %s\n", Argv[0]);
          return 1;
        }
        if (DebugLevel>=5 && DebugLevel<=9) {
          Options->Debug = TRUE;
        } else {
          Options->Debug = FALSE;
        }
        Argc--;
      } else if ((stricmp (Argv[0], "--quiet") == 0) || (stricmp (Argv[0], "-q") == 0)) {
        Options->Quiet = TRUE;
      } else if ((stricmp (Argv[0], "--dump") == 0) || (stricmp (Argv[0], "-d") == 0)) {
        //
        // -dump for dumping a ROM image. In this case, say that the device id
        // and vendor id are valid so we don't have to specify bogus ones on the
        // command line.
        //
        Options->DumpOption   = 1;

        Options->VendIdValid  = 1;
        Options->DevIdValid   = 1;
        FileFlags             = FILE_FLAG_BINARY;
      } else if ((stricmp (Argv[0], "-l") == 0) || (stricmp (Argv[0], "--class-code") == 0)) {
        //
        // Class code value for the next file in the list.
        // Make sure there's another parameter
        //
        if (Argc > 1) {
          //
          // No error checking on the return value. Could check for LONG_MAX,
          // LONG_MIN, or 0 class code value if desired. Check range (3 bytes)
          // at least.
          //
          ClassCode = (UINT32) strtol (Argv[1], NULL, 16);
          if (ClassCode & 0xFF000000) {
            Error (NULL, 0, 2000, "Invalid parameter", "Class code %s out of range!", Argv[1]);
            return STATUS_ERROR;
          }
        } else {
	        Error (NULL, 0, 2000, "Invalid parameter", "Missing class code value with %s!", Argv[0]);
          Usage ();
          return STATUS_ERROR;
        }

        Argv++;
        Argc--;
      } else if ((stricmp (Argv[0], "-r") == 0) || (stricmp (Argv[0], "--Revision") == 0)) {
        //
        // Code revision in the PCI data structure. The value is for the next
        // file in the list.
        // Make sure there's another parameter
        //
        if (Argc > 1) {
          //
          // No error checking on the return value. Could check for LONG_MAX,
          // LONG_MIN, or 0 value if desired. Check range (2 bytes)
          // at least.
          //
          CodeRevision = (UINT32) strtol (Argv[1], NULL, 16);
          if (CodeRevision & 0xFFFF0000) {
            Error (NULL, 0, 2000, "Invalid parameter", "Code revision %s out of range!", Argv[1]);
            return STATUS_ERROR;
          }
        } else {
	        Error (NULL, 0, 2000, "Invalid parameter", "Missing code revision value with %s!", Argv[0]);
          Usage ();
          return STATUS_ERROR;
        }

        Argv++;
        Argc--;
      } else if ((stricmp (Argv[0], "-p") == 0) || (stricmp (Argv[0], "-pci23") == 0)) {
        //
        // Default layout meets PCI 3.0 specifications, specifying this flag will for a PCI 2.3 layout.
        //
        mOptions.Pci23 = 1; 
      } else {
        Error (NULL, 0, 2000, "Invalid parameter", "Invalid option specified: %s", Argv[0]);
        Usage ();
        return STATUS_ERROR;
      }
    } else {
      //
      // Not a slash-option argument. Must be a file name. Make sure they've specified
      // -e or -b already.
      //
      if ((FileFlags & (FILE_FLAG_BINARY | FILE_FLAG_EFI)) == 0) {
        Error (NULL, 0, 2000, "Invalid parameter", "Missing -e or -b with input file %s!", Argv[0]);
        return STATUS_ERROR;
      }
      //
      // Create a new file structure
      //
      FileList = (FILE_LIST *) malloc (sizeof (FILE_LIST));
      if (FileList == NULL) {
        Error (NULL, 0, 4001, "Resource", "memory cannot be allocated!");
        return STATUS_ERROR;
      }
      
      //
      // set flag and class code for this image.
      //
      memset ((char *) FileList, 0, sizeof (FILE_LIST));
      FileList->FileName      = Argv[0];
      FileList->FileFlags     = FileFlags;
      FileList->ClassCode     = ClassCode;
      FileList->CodeRevision  = (UINT16) CodeRevision;
      ClassCode               = 0;
      CodeRevision            = 0;

      if (Options->FileList == NULL) {
        Options->FileList = FileList;
      } else {
        if (PrevFileList == NULL) {
          PrevFileList = FileList;
        } else {          
          PrevFileList->Next = FileList;
        }
      }

      PrevFileList = FileList;
    }
    //
    // Next argument
    //
    Argv++;
    Argc--;
  }

  //
  // Must have specified some files
  //
  if (Options->FileList == NULL) {
    Error (NULL, 0, 2000, "Invalid parameter", "Missing input file name!");
    Usage ();
    return STATUS_ERROR;
  }

  //
  // Make sure they specified a device ID and vendor ID
  //
  if (!Options->VendIdValid) {
    Error (NULL, 0, 2000, "Missing Vendor ID in command line", NULL);
    return STATUS_ERROR;
  }

  if (!Options->DevIdValid) {
    Error (NULL, 0, 2000, "Missing Device ID in command line", NULL);
    Usage ();
    return STATUS_ERROR;
  }

  return 0;
}

static
void
Version (
  VOID
  )
/*++

Routine Description:
  
  Print version information for this utility.

Arguments:

  None.

Returns:

  Nothing.
--*/
{
 fprintf (stdout, "%s Version %d.%d\n", UTILITY_NAME, UTILITY_MAJOR_VERSION, UTILITY_MINOR_VERSION);
}
   
static
void
Usage (
  VOID
  )
/*++

Routine Description:
  
  Print usage information for this utility.

Arguments:

  None.

Returns:

  Nothing.

--*/
{
  //
  // Summary usage
  //
  fprintf (stdout, "Usage: %s [options] [file name<s>] \n\n", UTILITY_NAME);
  
  //
  // Copyright declaration
  // 
  fprintf (stdout, "Copyright (c) 2007, Intel Corporation. All rights reserved.\n\n");

  //
  // Details Option
  //
  fprintf (stdout, "Options:\n");
  fprintf (stdout, "  -o FileName, --output FileName\n\
            File will be created to store the ouput content.\n");
  fprintf (stdout, "  -e EfiFileName\n\
            EFI PE32 image files.\n");
  fprintf (stdout, "  -ec EfiFileName\n\
            EFI PE32 image files and will be compressed.\n");
  fprintf (stdout, "  -b BinFileName\n\
            Legacy binary files.\n");
  fprintf (stdout, "  -l ClassCode\n\
            Hex ClassCode in the PCI data structure header.\n");
  fprintf (stdout, "  -r Rev\n\
            hex Revision in the PCI data structure header.\n");
  fprintf (stdout, "  -n\n\
            not to automatically set the LAST bit in the last file.\n");
  fprintf (stdout, "  -f VendorId\n\
            Hex PCI Vendor ID for the device OpROM.\n");
  fprintf (stdout, "  -i DeviceId\n\
            Hex PCI Device ID for the device OpROM.\n");
  fprintf (stdout, "  -p, --pci23\n\
            Default layout meets PCI 3.0 specifications, specifying this flag will for a PCI 2.3 layout.\n");
  fprintf (stdout, "  -d, --dump\n\
            Dump the headers of an existing option ROM image.\n");
  fprintf (stdout, "  -v, --verbose\n\
            Turn on verbose output with informational messages.\n");
  fprintf (stdout, "  --version\n\
            Show program's version number and exit.\n");
  fprintf (stdout, "  -h, --help\n\
            Show this help message and exit.\n");
  fprintf (stdout, "  -q, --quiet\n\
            Disable all messages except FATAL ERRORS.\n");
  fprintf (stdout, "  --debug [#,0-9]\n\
            Enable debug messages at level #.\n");  
}

static
void
DumpImage (
  FILE_LIST *InFile
  )
/*++

Routine Description:

  Dump the headers of an existing option ROM image

Arguments:

  InFile  - the file name of an existing option ROM image

Returns:

  none

--*/
{
  PCI_EXPANSION_ROM_HEADER      PciRomHdr;
  FILE                          *InFptr;
  UINT32                        ImageStart;
  UINT32                        ImageCount;
  EFI_PCI_EXPANSION_ROM_HEADER  EfiRomHdr;
  PCI_DATA_STRUCTURE            PciDs23;
  PCI_3_0_DATA_STRUCTURE        PciDs30;

  //
  // Open the input file
  //
  if ((InFptr = fopen (InFile->FileName, "rb")) == NULL) {
    Error (NULL, 0, 0001, "Error opening file", InFile->FileName);
    return ;
  }
  //
  // Go through the image and dump the header stuff for each
  //
  ImageCount = 0;
  for (;;) {
    //
    // Save our postition in the file, since offsets in the headers
    // are relative to the particular image.
    //
    ImageStart = ftell (InFptr);
    ImageCount++;

    //
    // Read the option ROM header. Have to assume a raw binary image for now.
    //
    if (fread (&PciRomHdr, sizeof (PciRomHdr), 1, InFptr) != 1) {
      Error (NULL, 0, 3001, "Not supported", "Failed to read PCI ROM header from file!");
      goto BailOut;
    }

    //
    // Dump the contents of the header
    //
    fprintf (stdout, "Image %d -- Offset 0x%X\n", ImageCount, ImageStart);
    fprintf (stdout, "  ROM header contents\n");
    fprintf (stdout, "    Signature              0x%04X\n", (UINT32) PciRomHdr.Signature);
    fprintf (stdout, "    PCIR offset            0x%04X\n", (UINT32) PciRomHdr.PcirOffset);
    //
    // Find PCI data structure
    //
    if (fseek (InFptr, ImageStart + PciRomHdr.PcirOffset, SEEK_SET)) {
      Error (NULL, 0, 3001, "Not supported", "Failed to seek to PCI data structure!");
      goto BailOut;
    }
    //
    // Read and dump the PCI data structure
    //
    memset (&PciDs23, 0, sizeof (PciDs23));
    memset (&PciDs30, 0, sizeof (PciDs30));
    if (mOptions.Pci23 == 1) {
      if (fread (&PciDs23, sizeof (PciDs23), 1, InFptr) != 1) {
        Error (NULL, 0, 3001, "Not supported", "Failed to read PCI data structure from file %s!", InFile->FileName);
        goto BailOut;
      }
    } else {
      if (fread (&PciDs30, sizeof (PciDs30), 1, InFptr) != 1) {
        Error (NULL, 0, 3001, "Not supported", "Failed to read PCI data structure from file %s!", InFile->FileName);
        goto BailOut;
      }
    }
    if (mOptions.Verbose) {
      VerboseMsg("Read PCI data structure from file %s", InFile->FileName);
    }

    //fprintf (stdout, "  PCI Data Structure\n");
    if (mOptions.Pci23 == 1) {
    fprintf (
      stdout,
      "    Signature              %c%c%c%c\n",
      (char) PciDs23.Signature,
      (char) (PciDs23.Signature >> 8),
      (char) (PciDs23.Signature >> 16),
      (char) (PciDs23.Signature >> 24)
      );
    fprintf (stdout, "    Vendor ID              0x%04X\n", PciDs23.VendorId);
    fprintf (stdout, "    Device ID              0x%04X\n", PciDs23.DeviceId);
    fprintf (stdout, "    Length                 0x%04X\n", PciDs23.Length);
    fprintf (stdout, "    Revision               0x%04X\n", PciDs23.Revision);
    fprintf (
      stdout,
      "    Class Code             0x%06X\n",
      (UINT32) (PciDs23.ClassCode[0] | (PciDs23.ClassCode[1] << 8) | (PciDs23.ClassCode[2] << 16))
      );
    fprintf (stdout, "    Image size             0x%X\n", PciDs23.ImageLength * 512);
    fprintf (stdout, "    Code revision:         0x%04X\n", PciDs23.CodeRevision);
    fprintf (stdout, "    Indicator              0x%02X", (UINT32) PciDs23.Indicator);
    } else {
    fprintf (
      stdout,
      "    Signature               %c%c%c%c\n",
      (char) PciDs30.Signature,
      (char) (PciDs30.Signature >> 8),
      (char) (PciDs30.Signature >> 16),
      (char) (PciDs30.Signature >> 24)
      );
    fprintf (stdout, "    Vendor ID               0x%04X\n", PciDs30.VendorId);
    fprintf (stdout, "    Device ID               0x%04X\n", PciDs30.DeviceId);
    fprintf (stdout, "    Length                  0x%04X\n", PciDs30.Length);
    fprintf (stdout, "    Revision                0x%04X\n", PciDs30.Revision);
    fprintf (stdout, "    DeviceListOffset        0x%02X\n", (UINT32) PciDs30.DeviceListOffset);    
    fprintf (
      stdout,
      "    Class Code              0x%06X\n",
      (UINT32) (PciDs30.ClassCode[0] | (PciDs30.ClassCode[1] << 8) | (PciDs30.ClassCode[2] << 16))
      );
    fprintf (stdout, "    Image size              0x%X\n", PciDs30.ImageLength * 512);
    fprintf (stdout, "    Code revision:          0x%04X\n", PciDs30.CodeRevision);
    fprintf (stdout, "    MaxRuntimeImageLength   0x%02X\n", (UINT32) PciDs30.MaxRuntimeImageLength);
    fprintf (stdout, "    ConfigUtilityCodeHeaderOffset 0x%02X\n", (UINT32) PciDs30.ConfigUtilityCodeHeaderOffset);
    fprintf (stdout, "    DMTFCLPEntryPointOffset 0x%02X\n", (UINT32) PciDs30.DMTFCLPEntryPointOffset);   
    fprintf (stdout, "    Indicator               0x%02X", (UINT32) PciDs30.Indicator);    
    }
    //
    // Print the indicator, used to flag the last image
    //
    if (PciDs23.Indicator == INDICATOR_LAST || PciDs30.Indicator == INDICATOR_LAST) {
      fprintf (stdout, "   (last image)\n");
    } else {
      fprintf (stdout, "\n");
    }
    //
    // Print the code type. If EFI code, then we can provide more info.
    //
    if (mOptions.Pci23 == 1) {
      fprintf (stdout, "    Code type              0x%02X", (UINT32) PciDs23.CodeType);
    } else {
      fprintf (stdout, "    Code type               0x%02X", (UINT32) PciDs30.CodeType); 
    }
    if (PciDs23.CodeType == PCI_CODE_TYPE_EFI_IMAGE || PciDs30.CodeType == PCI_CODE_TYPE_EFI_IMAGE) {
      fprintf (stdout, "   (EFI image)\n");
      //
      // Re-read the header as an EFI ROM header, then dump more info
      //
      fprintf (stdout, "  EFI ROM header contents\n");
      if (fseek (InFptr, ImageStart, SEEK_SET)) {
        Error (NULL, 0, 5001, "Failed to re-seek to ROM header structure!");
        goto BailOut;
      }

      if (fread (&EfiRomHdr, sizeof (EfiRomHdr), 1, InFptr) != 1) {
        Error (NULL, 0, 5001, "Failed to read EFI PCI ROM header from file!");
        goto BailOut;
      }
      //
      // Now dump more info
      //
      fprintf (stdout, "    EFI Signature          0x%04X\n", EfiRomHdr.EfiSignature);
      fprintf (
        stdout,
        "    Compression Type       0x%04X ",
        (UINT32) EfiRomHdr.CompressionType
        );
      if (EfiRomHdr.CompressionType == EFI_PCI_EXPANSION_ROM_HEADER_COMPRESSED) {
        fprintf (stdout, "(compressed)\n");
      } else {
        fprintf (stdout, "(not compressed)\n");
      }

      fprintf (
        stdout,
        "    Machine type           0x%04X (%s)\n",
        EfiRomHdr.EfiMachineType,
        GetMachineTypeStr (EfiRomHdr.EfiMachineType)
        );
      fprintf (
        stdout,
        "    Subsystem              0x%04X (%s)\n",
        EfiRomHdr.EfiSubsystem,
        GetSubsystemTypeStr (EfiRomHdr.EfiSubsystem)
        );
      fprintf (
        stdout,
        "    EFI image offset       0x%04X (@0x%X)\n",
        (UINT32) EfiRomHdr.EfiImageHeaderOffset,
        (UINT32) (EfiRomHdr.EfiImageHeaderOffset + ImageStart)
        );

    } else {
      //
      // Not an EFI image
      //
      fprintf (stdout, "\n");
    }
    //
    // If code type is EFI image, then dump it as well?
    //
    // if (PciDs.CodeType == PCI_CODE_TYPE_EFI_IMAGE) {
    // }
    //
    // If last image, then we're done
    //
    if (PciDs23.Indicator == INDICATOR_LAST || PciDs30.Indicator == INDICATOR_LAST) {
      goto BailOut;
    }
    //
    // Seek to the start of the next image
    //
    if (mOptions.Pci23 == 1) {
      if (fseek (InFptr, ImageStart + (PciDs23.ImageLength * 512), SEEK_SET)) {
        Error (NULL, 0, 3001, "Not supported", "Failed to seek to next image!");
        goto BailOut;
      }
    } else {
      if (fseek (InFptr, ImageStart + (PciDs30.ImageLength * 512), SEEK_SET)) {
        Error (NULL, 0, 3001, "Not supported", "Failed to seek to next image!");
        goto BailOut;
      }
    }
  }

BailOut:
  fclose (InFptr);
}

char *
GetMachineTypeStr (
  UINT16    MachineType
  )
/*++

Routine Description:

  GC_TODO: Add function description

Arguments:

  MachineType - GC_TODO: add argument description

Returns:

  GC_TODO: add return values

--*/
{
  int Index;

  for (Index = 0; mMachineTypes[Index].Name != NULL; Index++) {
    if (mMachineTypes[Index].Value == MachineType) {
      return mMachineTypes[Index].Name;
    }
  }

  return "unknown";
}

static
char *
GetSubsystemTypeStr (
  UINT16  SubsystemType
  )
/*++

Routine Description:

  GC_TODO: Add function description

Arguments:

  SubsystemType - GC_TODO: add argument description

Returns:

  GC_TODO: add return values

--*/
{
  int Index;

  for (Index = 0; mSubsystemTypes[Index].Name != NULL; Index++) {
    if (mSubsystemTypes[Index].Value == SubsystemType) {
      return mSubsystemTypes[Index].Name;
    }
  }

  return "unknown";
}
