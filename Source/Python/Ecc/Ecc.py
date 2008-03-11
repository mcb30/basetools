## @file
# This file is used to be the main entrance of ECC tool
#
# Copyright (c) 2008, Intel Corporation
# All rights reserved. This program and the accompanying materials
# are licensed and made available under the terms and conditions of the BSD License
# which accompanies this distribution.  The full text of the license may be found at
# http://opensource.org/licenses/bsd-license.php
#
# THE PROGRAM IS DISTRIBUTED UNDER THE BSD LICENSE ON AN "AS IS" BASIS,
# WITHOUT WARRANTIES OR REPRESENTATIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
#

##
# Import Modules
#
import os
from optparse import OptionParser
import Common.EdkLogger as EdkLogger
import Database
from Configuration import Configuration
from Check import Check
import EccGlobalData
import time
#import c

## Ecc
#
# This class is used to define Ecc main entrance
#
# @param object:          Inherited from object class
#
class Ecc(object):
    def __init__(self):
        # Version and Copyright
        self.VersionNumber = "0.01"
        self.Version = "%prog Version " + self.VersionNumber
        self.Copyright = "Copyright (c) 2008, Intel Corporation  All rights reserved."
        
        self.ConfigFile = 'config.ini'
        self.OutputFile = 'output.txt'
        
        #
        # Initialize log system
        #
        EdkLogger.Initialize()
        EdkLogger.quiet(time.strftime("%H:%M:%S, %b.%d %Y ", time.localtime()) + "[00:00]" + "\n")
        
        #
        # Parse the options and args
        #
        self.ParseOption()

        #
        # Generate checkpoints list
        #
        EccGlobalData.gConfig = Configuration(self.ConfigFile)
        
        #
        # Build ECC database
        #
        self.BuildDatabase()
        
        #
        # Start to check
        #
        self.Check()
        
        #
        # Show report
        #
        self.GenReport()
        
        #
        # Close Database
        #
        EccGlobalData.gDb.Close()

    ##
    #
    # Build the database for target
    #
    def BuildDatabase(self):
        EdkLogger.quiet("Parsing target ...")
        EccGlobalData.gDb = Database.Database(Database.DATABASE_PATH)
        EccGlobalData.gDb.InitDatabase()
        #c.CollectSourceCodeDataIntoDB(EccGlobalData.gTarget)
        EdkLogger.quiet("Parsing target done!")

    ##
    #
    # Check each checkpoint
    #
    def Check(self):
        EdkLogger.quiet("Checking ...")
        EccCheck = Check()
        EccCheck.Check()
        EdkLogger.quiet("Checking  done!")
    
    ##
    #
    # Generate the scan report
    #
    def GenReport(self):
        EdkLogger.quiet("Generating report ...")
        EdkLogger.quiet("Generating report done!")
    
    ## ParseOption
    #
    # Parse options
    #
    def ParseOption(self):
        EdkLogger.quiet("Loading ECC configuration ... done")
        (Options, Target) = self.EccOptionParser()
        
        #
        # Check workspace envirnoment
        #
        if "WORKSPACE" not in os.environ:
            EdkLogger.error("ECC", ATTRIBUTE_NOT_AVAILABLE, "Environment variable not found", 
                            ExtraData="WORKSPACE")
        else:
            EccGlobalData.gWorkspace = os.path.normpath(os.getenv("WORKSPACE"))
            if not os.path.exists(EccGlobalData.gWorkspace):
                EdkLogger.error("ECC", FILE_NOT_FOUND, ExtraData="WORKSPACE = %s" % EccGlobalData.gWorkspace)
            os.environ["WORKSPACE"] = EccGlobalData.gWorkspace
        #
        # Set log level
        #
        self.SetLogLevel(Options)
        
        #
        # Set other options
        #
        if Options.ConfigFile != None:
            self.ConfigFile = Options.ConfigFile
        if Options.OutputFile != None:
            self.OutputFile = Options.OutputFile
        if Options.Target != None:
            EccGlobalData.gTarget = Options.Target
        else:
            EdkLogger.error("Ecc", EdkLogger.ECC_ERROR, "A target workspace must be specified!")
           
    ## SetLogLevel
    #
    # Set current log level of the tool based on args
    #
    # @param Option:  The option list including log level setting 
    #
    def SetLogLevel(self, Option):
        if Option.verbose != None:
            EdkLogger.SetLevel(EdkLogger.VERBOSE)
        elif Option.quiet != None:
            EdkLogger.SetLevel(EdkLogger.QUIET)
        elif Option.debug != None:
            EdkLogger.SetLevel(Option.debug + 1)
        else:
            EdkLogger.SetLevel(EdkLogger.INFO)    

    ## Parse command line options
    #
    # Using standard Python module optparse to parse command line option of this tool.
    #
    # @retval Opt   A optparse.Values object containing the parsed options
    # @retval Args  Target of build command
    #
    def EccOptionParser(self):
        Parser = OptionParser(description = self.Copyright, version = self.Version, prog = "Ecc.exe", usage = "%prog [options]")
        Parser.add_option("-t", "--target sourcepath", action="store", type="string", dest='Target',
            help="Check all files under the target workspace.")
        Parser.add_option("-c", "--config filename", action="store", type="string", dest="ConfigFile",
            help="Specify a configuration file. Defaultly use config.ini under ECC tool directory.")
        Parser.add_option("-o", "--outfile filename", action="store", type="string", dest="OutputFile",
            help="Specify the name of an output file, if and only if one filename was specified.")
    
        Parser.add_option("-l", "--log filename", action="store", dest="LogFile", help="""If specified, the tool should emit the changes that 
                                                                                          were made by the tool after printing the result message. 
                                                                                          If filename, the emit to the file, otherwise emit to 
                                                                                          standard output. If no modifications were made, then do not 
                                                                                          create a log file, or output a log message.""")
        Parser.add_option("-q", "--quiet", action="store_true", type=None, help="Disable all messages except FATAL ERRORS.")
        Parser.add_option("-v", "--verbose", action="store_true", type=None, help="Turn on verbose output with informational messages printed, "\
                                                                                   "including library instances selected, final dependency expression, "\
                                                                                   "and warning messages, etc.")
        Parser.add_option("-d", "--debug", action="store", type="int", help="Enable debug messages at specified level.")
    
        (Opt, Args)=Parser.parse_args()
        
        return (Opt, Args)

##
#
# This acts like the main() function for the script, unless it is 'import'ed into another
# script.
#
if __name__ == '__main__':
    Ecc = Ecc()
    