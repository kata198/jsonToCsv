#!/usr/bin/env python
'''
    Copyright (c) 2017 Timothy Savannah All Rights Reserved

    Licensed under terms of LGPLv3.

    This is some example code which shows how to use the "json_to_csv" module.
'''

import json
import os
import sys


from json_to_csv import JsonToCsv, ParseError

# NULL_VALUE - This is how we will represent when a value is unreachable, undefined, or actually has a value of (null) in the data.
NULL_VALUE = "NULL"


##### SOME SAMPLE JSON DATA, CONTAINING ONE INSTANCE ####

#  In main, we will use "example.json" which contains several.
#  Each instance need not contain all the fields we want to extract,
#    and if a field is unreachable, it will be assigned None, which when we convert to a string will take on
#    the value assigned to #NULL_VALUE above.
SAMPLE_JSON_DATA = '''
{
    "results": {

        "instances": [
                      {
                        "hostname": "examplehost1.example.com",
                        "ip": "192.168.0.1",
                        "attributes": [
                               {"name": "domain", "value": "test"},
                               {"name": "owner", "value": "James99"},
                               {"name": "status", "value": "Complete"}
                         ],
                         "puppet_data" : {
                             "hostgroup" : "at_test",
                             "last_executed" : "1/1/2011 12:51:55"
                         }
                       }
          ]
    }
}
'''
SAMPLE_JSON = json.loads(SAMPLE_JSON_DATA)

# These are the headers of the fields we will extract.
CSV_HEADERS = "Hostname,IpAddr,Status,PuppetHostGroup,Domain,Owner"

# This is the "parse str" using the json_to_csv meta-language for accurate extraction ( see README or from json_to_csv.help import FORMAT_HELP )
#   explained verbosely in comments following:
PARSE_STR = '''
        ."results"[
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
        ]
'''
# Can also be written as one-liner:
#  ".results"[ +"instances"["hostname", "ip" /"attributes"["name"="status" "value"], ."puppet_data"["hostgroup"], /"attributes"["name"="domain" "value"], /"attributes"["name"="owner" "value"]] ]

########################                         ###############################
################# VERBOSE EXPLANATION OF FORMAT STR: ###########################
########################                         ###############################

# ."results"[               # First, ascend into a map (dict) [ . operator ] under keyname, "results"
#       +"instances"[       # "+" defines the "line item". At this point we start iterating for each element of the "instances" list.
#            "hostname",    # A plain key-name defines a key to print at current level. So, we will print "hostname" directly inside "instances"
#            "ip"           # Next, we will print "ip"
#            /"attributes"["name"="status"      # We will descend into a list-of-maps named "attributes" [ / operator ],
#                                               #   searching for where the key "name" equals "status".
#                                               # On the first map found that satisfies that condition, 
#                                               #   we will continue starting in that map until the bracket close "]"
#               "value"     # Print the value of the key "value" at current level
#            ],             # We return to the previous level (back to the current item in the "instances" array)
#            ."puppet_data"[        # Descend into a map at current level [ . operator ] under the key "puppet_data"
#               "hostgroup"         # Print the value of the key "hostgroup"
#            ],             # Return to previous level ( current item in "instances" array)
#            /"attributes"["name"="domain"      # Descend into list-of-maps [ / operator ] under key "attributes",
#                                               # and stop where the key "name" has a value of "domain"
#               "value"     # Print the value of the "value" key at current level
#            ],             # Return to previous level ( current item in "instances" array )
#            /"attributes"["name"="owner"       # Descend into list-of-maps [ / operator ] under key "attributes",
#                                               # and stop where the key "name" has a value of "owner"
#               "value"     # Print the value of the "value" key at current level
#            ]              # Go back to previous level ( current item in "instances" array )
#        ]                  # Since this closes the line item, we repeat the loop starting back at the open square bracket after
#                           #   +"instances", i.e. we continue to the next item and line.
#                           # Once all items in the "instances" array have been iterated over, we will go up to parent level (the "results" map at root level)
#  ]                        # We close the final item, and we are done!



# IS_DEBUG = Set to True or pass --debug on cli to output some extra info
IS_DEBUG = False

if __name__ == '__main__':

    if '--debug' in sys.argv:
        IS_DEBUG = True

    dirName = os.path.dirname(__file__)
    if dirName and os.getcwd() != dirName:
        os.chdir(dirName)

    if not os.path.exists('example.json'):
        sys.stderr.write('ABORTING: Cannot find sample json file: example.json\n')
        sys.exit(1)


    # Try to parse format string
    try:
        parser = JsonToCsv(PARSE_STR, nullValue=NULL_VALUE, debug=IS_DEBUG)
    except ParseError as pe:
        # Got a readable error, print it.
        sys.stderr.write('Error in format str: %s\n' %(str(pe),))
        sys.exit(1)

    # Read data from stdin
    with open('example.json', 'rt') as f:
        contents = f.read()



    # Parse that data, and print the csv string.
    #   First, show "convertToCsv" which goes straight to string (when asLines=False)
    try:
        csvDataStr = parser.convertToCsv(contents)
    except ParseError as pe:
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
