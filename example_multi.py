#!/usr/bin/env python
'''
    Copyright (c) 2017 Timothy Savannah All Rights Reserved

    Licensed under terms of LGPLv3.

    This is some example code which shows how to use the "json_to_csv" module.
'''

import json
import os
import sys


from json_to_csv import JsonToCsv, FormatStrParseError

# NULL_VALUE - This is how we will represent when a value is unreachable, undefined, or actually has a value of (null) in the data.
NULL_VALUE = "NULL"


# These are the headers of the fields we will extract.
CSV_HEADERS = "Date,PreItem,Hostname,IpAddr,Status,PuppetHostGroup,Domain,Owner,PostItem,Name"

# This is the "parse str" using the json_to_csv meta-language for accurate extraction ( see README or from json_to_csv.help import FORMAT_HELP )
#   explained verbosely in comments following:
PARSE_STR = '''
        "date",     +"results"[
                 

        
                  
          "myBeforeKey",
            +"instances"[
                "hostname",
                "ip"
                /"attributes"["name"="status"
                    "value"
                ],
                ."puppet_data"[
                    "hostgroup"
                ],
                /"attributes"["name"="domain"
                    "value"
                ],
                /"attributes"["name"="owner"
                    "value"
                ]
            ]
            "myAfterKey"
        ],
        "name",
'''
########################                         ###############################
################# VERBOSE EXPLANATION OF FORMAT STR: ###########################
########################                         ###############################

PARSE_STR = '''
        "date",             # First element of every line will be the value of


                            #  "date" at the top level
        +"results"[         # Iterate over each member of the list under "results"
          "myBeforeKey",    # Include "myBeforeKey" as the next item in every line
            +"instances"[   # Iterate over each member of the list under "instances"
                "hostname", # Include "hostname" under "instances" in each line
                "ip"        # Next key to add is "ip"
                /"attributes"["name"="status"  # Descend into a list-of-maps under "attributes" and look
                                               #  for where the key "name" has the value "status"
                    "value"                    # In the matched-map, print the value of the key "value"
                ],                             # Leave this matched map, return to one level up
                ."puppet_data"[                # Descend into map found at "puppet_data" key
                    "hostgroup"                # Print the "hostgroup" key at this level
                ],                             # Return to previous level
                /"attributes"["name"="domain"  # Descend into a list-of-maps under "attributes" and look
                                               #  for where the key "name" has the value "domain"
                    "value"                    # Print the "value" key in this matched map
                ],                             # Go back up to previous level
                /"attributes"["name"="owner"   # Descend into a list-of-maps at "attributes" and look
                                               #  for where the key "name" has the value "owner"
                    "value"                    # Print the key "value" at this level
                ]                              # Go back to previous level
            ]                                  # Go back to previous level
            "myAfterKey"                       # Append to all previous lines the value of key "myAfterKey"
        ],                                     # Go back up a level
        "name"                                # Append to all previous lines the value of key "name"
'''


# IS_DEBUG = Set to True or pass --debug on cli to output some extra info
IS_DEBUG = False

if __name__ == '__main__':

    if '--debug' in sys.argv:
        IS_DEBUG = True

    dirName = os.path.dirname(__file__)
    if dirName and os.getcwd() != dirName:
        os.chdir(dirName)

    if not os.path.exists('example_multi.json'):
        sys.stderr.write('ABORTING: Cannot find sample json file: example_multi.json\n')
        sys.exit(1)


    # Try to parse format string
    try:
        parser = JsonToCsv(PARSE_STR, nullValue=NULL_VALUE, debug=IS_DEBUG)
    except FormatStrParseError as pe:
        # Got a readable error, print it.
        sys.stderr.write('Error in format str: %s\n' %(str(pe),))
        sys.exit(1)

    # Read data from stdin
    with open('example_multi.json', 'rt') as f:
        contents = f.read()



    # Parse that data, and print the csv string.
    #   First, show "convertToCsv" which goes straight to string (when asLines=False)
    try:
        csvDataStr = parser.convertToCsv(contents)
    except FormatStrParseError as pe:
        sys.stderr.write('Error in parsing: %s\n' %(str(pe),))
        sys.exit(1)

    sys.stdout.write('\n\n')


    # Output extracted data in CSV format
    print ( "As CSV:\n" )

    print ( CSV_HEADERS )
    print ( csvDataStr )

    print ( "\n\n" )

    # Now, show the more verbose approach.
    #   Extract as raw data, a list (lines) of lists (fields)
    #   We will use this to convert to various strings for output.
    csvData = parser.extractData(contents)

    # Show that this can easily be converted to the same string as above:
    csvDataStr2 = JsonToCsv.dataToStr(csvData)

    assert csvDataStr == csvDataStr2 , "Got different results? Also.... Got Milk?"

    # Output extracted data in TSV format
    tsvDataStr = JsonToCsv.dataToStr(csvData, separator='\t')

    print ( "As TSV:\n" )

    print ( '\t'.join(CSV_HEADERS.split(',')) )
    print ( tsvDataStr )


    print ( "\n\n" )

    print ( "As Table:\n" )

    # Make a pretty table

    # First column is longer, so give it extra width.
    firstCol = True

    FIRST_COL_WIDTH = 24
    FIRST_COL_STR_OPER = '%' + str(FIRST_COL_WIDTH) + 's'

    COL_WIDTH = 17
    COL_STR_OPER = '%' + str(COL_WIDTH) + 's'


    headerSplit = CSV_HEADERS.split(',')
    numHeaders = len(headerSplit)

    # Enumerate the headers
    for i in range(numHeaders):
        header = headerSplit[i]

        if firstCol is True:
            oper = FIRST_COL_STR_OPER
            firstCol = False
        else:
            oper = COL_STR_OPER
        sys.stdout.write( oper % (header, ))

        if i != numHeaders - 1:
            sys.stdout.write('\t')

    sys.stdout.write('\n')

    # Draw an underline under heach header
    sys.stdout.write('-' * FIRST_COL_WIDTH)
    sys.stdout.write('\t')
    sys.stdout.write('\t'.join(['-' * COL_WIDTH for i in range(numHeaders-1)]))
    sys.stdout.write('\n')


    # Now print the values, one line at a time.
    #   Remember, csvData is a list of lines, each line being a list of fields
    for line in csvData:
        firstCol = True
        for i in range(numHeaders):
            field = line[i]

            if firstCol is True:
                oper = FIRST_COL_STR_OPER
                firstCol = False
            else:
                oper = COL_STR_OPER
            sys.stdout.write( oper % (field, ))
            if i != numHeaders - 1:
                sys.stdout.write('\t')
        sys.stdout.write('\n')

    sys.stdout.write('\n\n')
