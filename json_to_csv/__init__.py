'''
    Copyright (c) 2017 Timothy Savannah All Rights Reserved

    Licensed under terms of LGPLv3.

    json_to_csv - Module for converting json data to csv data, and various supplementry methods.

    Resulting csv will confirm to RFC 4180 "Common format for MIME Type for Comma-Separated Values (CSV) Files

    May also be used to just extract data into lists.

'''

# vim: set ts=4 sw=4 st=4 expandtab :

import copy
import json
import sys
import re
import traceback

from collections import defaultdict, deque

from ._private import Rule, Level, Level_Map, Level_ListMap, LineItem

__version__ = '1.0.1'
__version_tuple__ = (1, 0, 1)


# Public items
__all__ = ('FormatStrParseError', 'JsonToCsv', )




class JsonToCsv(object):
    '''
        JsonToCsv - Public class containing methods for dealing with converting
            Json to csv data, merging data, etc.

            Designed to produce RFC 4180 csv output from json data using a meta language.

    '''

    def __init__(self, formatStr, nullValue='', debug=False):
        '''
            __init__ - Create a JsonToCsv object.

            @param formatStr <str> - The format formatStr for the json data to be converted.

            @param nullValue <str> Default empty string - The value to assign to a "null" result.

            @param debug <bool> Default False - If True, will output some debug data on stderr.
        '''

        # format pattern
        self.formatStr = formatStr

        # The value to assign to a "null"-valued or unreachable field.
        self.nullValue = nullValue

        # debug flag
        self.debug = debug

        # lineItems - Tuple of (LineItem objects)
        #   each "preLineItemLevels" describes the levels used by Rule to walk from the previous
        #   point to the current line item key on which to iterate.
        self.lineItems = deque()

        # preLineItemRules - Any rules found prior to descending into the first line item
        self.preLineItemRules = []

        # postLineItemRules - Any rules found AFTER closing the first line item
        self.postLineItemRules = []

        # Fill the private attributes above
        self.__parsePattern()


    ################################################
    #######         Public Methods           #######
    ################################################


    def extractData(self, data):
        '''
            extractData - Return a list of lists. The outer list represents lines, the inner list data points.

                e.x.  returnData[0] is first line,  returnData[0][2] is first line third data point.

                @param data <string/dict> - Either a string of JSON data, or a dict.

                NOTE: This is the recommended method to be used. You can pass the data to
                  JsonToCsv.dataToStr to convert to csv, tsv, and other formats.

                @return list<list<str>> - List of lines, each line containing a list of datapoints.
        '''
        # Get data in right format
        if not isinstance(data, dict):
            obj = json.loads(data)
        else:
            obj = data

        existingFields = [rule(obj) for rule in self.preLineItemRules]

        if len(self.lineItems):
            lineItems = copy.copy(self.lineItems)

            firstLineItem = lineItems.popleft()


            lines = self._followLineItems(obj, firstLineItem, lineItems, existingFields)
        else:
            lines = [existingFields[:]]

        if self.postLineItemRules:
            postFields = [rule(obj) for rule in self.postLineItemRules]

            for line in lines:
                line += postFields

        return lines

    def convertToCsv(self, data, quoteFields="smart", lineSeparator='\r\n'):
        '''
            convertToCsv - Convert given data to csv.

               Alias to calling:
                 extractData
            
               and then passing those results to:
                 dataToStr

            @param data <string/dict> - Either a string of json data, or a dict

            @param quoteFields <bool or 'smart'> Default 'smart' -
                If False, fields will not be quoted (thus a comma or newline, etc will break the output, but it looks neater on screen)
                If True, fields will always be quoted (protecting against commas, allows values to contain newlines, etc)
                If 'smart' (default), the need to quote fields will be auto-determined. This may take slighly longer on HUGE datasets,
                  but is generally okay.

            @param lineSeparator <str> - This will separate the lines. RFC4180 defines CRLF as the preferred ending, but implementations
                can vary (i.e. unix generally just uses '\n'). If you plan to have newlines ('\n') in the data, I suggest using '\r\n' as
                the lineSeparator as otherwise many implementations (like python's own csv module) will swallow the newline within the data.

            @return <list/str> - see "asList" param above.
        '''

        lines = self.extractData(data)

        return JsonToCsv.dataToStr(lines, separator=',', quoteFields=quoteFields, lineSeparator=lineSeparator)

    ################################################
    #######      Static Public Methods       #######
    ################################################

    @staticmethod
    def dataToStr(csvData, separator=',', quoteFields="smart", lineSeparator='\r\n'):
        '''
            dataToStr - Convert a list of lists of csv data to a string.

            @param csvData list<list> - A list of lists, first list is lines, inner-list are values.

              This is the data returned by JsonToCsv.extractData

            @param separator <str> - Default ',' this is the separator used between fields (i.e. would be a tab in TSV format)

            @param quoteFields <bool or 'smart'> Default 'smart' -
                If False, fields will not be quoted (thus a comma or newline, etc will break the output, but it looks neater on screen)
                If True, fields will always be quoted (protecting against commas, allows values to contain newlines, etc)
                If 'smart' (default), the need to quote fields will be auto-determined. This may take slighly longer on HUGE datasets,
                  but is generally okay. Quotes within a field (") will be replaced with two adjacent quotes ("") as per RFC4180

                  Use 'smart' unless you REALLY need to specify otherwise, as 'smart' will always produce RFC4180 csv files

            @param lineSeparator <str> - This will separate the lines. RFC4180 defines CRLF as the preferred ending, but implementations
                can vary (i.e. unix generally just uses '\n'). If you plan to have newlines ('\n') in the data, I suggest using '\r\n' as
                the lineSeparator as otherwise many implementations (like python's own csv module) will swallow the newline within the data.


            @return str - csv data
        '''
        # TODO: Maybe support other formats? We would have to handle converting csv -> list<list> though,
        #  which is probably outside the scope of this module.
        if not isinstance(csvData, list) or not isinstance(csvData[0], list):
            raise ValueError('csvData is not a list-of-lists. dataToStr is meant to convert the return of "extractData" method to csv data.')

        if quoteFields not in ('smart', True, False):
            raise ValueError('Unknown value "%s" for quoteFields. Should be "smart", True, or False.' %(repr(quoteFields,)))

        if quoteFields == 'smart':
            lines = []

            flatData = ''.join([''.join(items) for items in csvData])

            reqSmartQuoteRe = re.compile('(%s|[\\r\\n])' %(separator,))

            if bool(reqSmartQuoteRe.search(flatData)):
                quoteFields = True
            else:
                quoteFields = False

        if quoteFields is False:
            # Each line is the comma-joining (or whatever #separator is) of its values
            lines = [separator.join(items) for items in csvData]

        else:
            # RFC 4180 Specifies that if quotes are found in the data and
            #   the data is being quoted, than any quotes within the data must be replaced with double quote ("")
            lines = [separator.join(['"%s"' %(item.replace('"', '""'), ) for item in items]) for items in csvData]

        return lineSeparator.join(lines)

    @staticmethod
    def joinCsv(csvData1, joinFieldNum1, csvData2, joinFieldNum2):
        '''
            joinCsv - Join two sets of csv data based on a common field value in the two sets.

              csvData should be a list of list (1st is lines, second is items). Such data is gathered by using JsonToCsv.extractData method

              Combined data will append the fields of csvData2 to csvData1, omitting the common field from csvData2

              @param csvData1 list<list> - The "primary" data set

              @param joinFieldNum1 <int> - The index of the common field in csvData1

              @param csvData2 list<list> - The secondary data set

              @param joinFieldNum2 <int> - The index of the common field in csvData2

              @return tuple( mergedData [list<list>], onlyCsvData1 [list<list>], onlyCsvData2 [list<list>] )

                Return is a tuple of 3 elements. The first is the merged csv data where a join field matched.
                 The second is the elements only present in csvData1
                 The third is the elements only present in csvData2

              @raises ValueError - If csvData1 or csvData2 are not in the right format (list of lists)
              @raises KeyError   - If there are duplicate keys preventing a proper merge


              NOTE: each csvData MUST have unique values in the "join field", or it cannot join.

                Maybe try out something new for today, and check out "multiJoinCsv" function. 

                Use multiJoinCsv to link all matches in csvData1 to all matches in csvData2 where join fields match.

                JsonToCsv.findDuplicates will identify duplicate values for a given joinfield.
                  So you can have something like:

                  myCsvData = JsonToCsv.extractData(....)
                  joinFieldNum = 3  # Example, 4th field is the field we will join on

                  myCsvDataDuplicateLines = JsonToCsv.findDuplicates(myCsvData, joinFieldNum, flat=True)
                  if myCsvDataDuplicateLines:
                      myCsvDataUniq = [line for line in myCsvData if line not in myCsvDataDuplicateLines]
                  else:
                      myCsvDataUniq = myCsvData

        '''

        # TODO: Maybe support other formats? Probably not.
        if not isinstance(csvData1, list) or not isinstance(csvData1[0], list):
            raise ValueError('csvData1 is not a list of lists, as expected. Use extractData to gather lists of lists for this method.')
        if not isinstance(csvData2, list) or not isinstance(csvData2[0], list):
            raise ValueError('csvData2 is not a list of lists, as expected. Use extractData to gather lists of lists for this method.')


        # Map of all csvData1Key : csvData1Value
        csvData1Map = {}

        # Just the keys for csvData2
        csvData2Keys = set()

        onlyData1 = []
        onlyData2 = []
        combinedData = []

        # Extract the "joinKey" from the csvData1 (left) into csvData1Map
        for data in csvData1:

            joinFieldData = data[joinFieldNum1]
            # If duplicate found we cannot continue the join
            if joinFieldData in csvData1Map:
                raise KeyError('Duplicate data in joinField %d on csvData1: %s' %(joinFieldNum1, joinFieldData))

            # Copy data (list-by-ref)
            csvData1Map[joinFieldData] = data[:]


        # Extract the "joinKey" from csvData2, and merge if possible
        for data in csvData2:
            # Copy data (list-by-ref)

            joinFieldData = data[joinFieldNum2]
            if joinFieldData in csvData2Keys:
                raise KeyError('Duplicate data in joinField %d on csvData2: %s' %(joinFieldNum2, joinFieldData))
            csvData2Keys.add(joinFieldData)

            # If we have a match on left == right, 
            #   merge the data (omitting the joinField in dataSet2 [right] )
            if joinFieldData in csvData1Map:
                newData = data[ :joinFieldNum2] + data[joinFieldNum2 + 1 :]
                combinedData.append(csvData1Map[joinFieldData] + newData)
            else:
                # Otherwise, this data only exists in dataset 2
                onlyData2.append(data[:])

        # Find what was only in dataset 1
        onlyData1Keys = set(csvData1Map.keys()).difference(csvData2Keys)
        for key in onlyData1Keys:
            onlyData1.append(csvData1Map[key])

        # Return results
        return (combinedData, onlyData1, onlyData2)

    @staticmethod
    def multiJoinCsv(csvData1, joinFieldNum1, csvData2, joinFieldNum2):
        '''

            multiJoinCsv - Join two sets of csv data based on a common field value, but this time merge any results, i.e. if key is repeated on A then you'd have:

               AA and AB.


              csvData should be a list of list (1st is lines, second is items). Such data is gathered by using JsonToCsv.extractData method

              Combined data will append the fields of csvData2 to csvData1, omitting the common field from csvData2

              @param csvData1 list<list> - The "primary" data set

              @param joinFieldNum1 <int> - The index of the common field in csvData1

              @param csvData2 list<list> - The secondary data set

              @param joinFieldNum2 <int> - The index of the common field in csvData2

              @return tuple( mergedData [list<list>], onlyCsvData1 [list<list>], onlyCsvData2 [list<list>] )

                Return is a tuple of 3 elements. The first is the merged csv data where a join field matched.
                 The second is the elements only present in csvData1
                 The third is the elements only present in csvData2

              @raises ValueError - If csvData1 or csvData2 are not in the right format (list of lists)

        '''

        # TODO: Maybe support other formats? Probably not.
        if not isinstance(csvData1, list) or not isinstance(csvData1[0], list):
            raise ValueError('csvData1 is not a list of lists, as expected. Use extractData to gather lists of lists for this method.')
        if not isinstance(csvData2, list) or not isinstance(csvData2[0], list):
            raise ValueError('csvData2 is not a list of lists, as expected. Use extractData to gather lists of lists for this method.')


        # Map of all csvData1Key : csvData1Value
        csvData1Map = defaultdict(list)
        csvData2Map = defaultdict(list)

        # Just the keys for csvData2
        csvData2Keys = set()

        onlyData1 = []
        onlyData2 = []
        combinedData = []

        # Extract the "joinKey" from the csvData1 (left) into csvData1Map
        for data in csvData1:

            joinFieldData = data[joinFieldNum1]

            # Copy data (list-by-ref)
            csvData1Map[joinFieldData].append(data[:])


        # Extract the "joinKey" from csvData2, and merge if possible
        for data in csvData2:
            # Copy data (list-by-ref)
            data = data[:]

            joinFieldData = data[joinFieldNum2]

            csvData2Map[joinFieldData].append(data)

            # If we have a match on left == right, 
            #   merge the data (omitting the joinField in dataSet2 [right] )
            if joinFieldData not in csvData1Map:
                # Otherwise, this data only exists in dataset 2
                onlyData2.append(data)

        commonKeys = set(csvData1Map.keys()).intersection(set(csvData2Map.keys()))

        for key in commonKeys:
            csvDataRows1 = csvData1Map[key]

            for row1 in csvDataRows1:
                row1 = row1[:]
                for row2 in csvData2Map[key]:
                    row2 = row2[:]

                    newData = row2[ :joinFieldNum2] + row2[joinFieldNum2 + 1 :]

                    combinedData.append(row1 + newData)
                    

        csvData2Keys = list(csvData2Map.keys())

        # Find what was only in dataset 1
        onlyData1Keys = set(csvData1Map.keys()).difference(csvData2Keys)
        for key in onlyData1Keys:
            onlyData1 += csvData1Map[key]

        # Return results
        return (combinedData, onlyData1, onlyData2)

    @staticmethod
    def findDuplicates(csvData, fieldNum, flat=False):
        '''
            findDuplicates - Find lines with duplicate values in a specific field number.

                This is useful to strip duplicates before using JsonToCsv.joinCsv
                  which requires unique values in the join field.

                  @see JsonToCsv.joinCsv for example code


                @param csvData list<list<str>> - List of lines, each line containing string field values.

                    JsonToCsv.extractData returns data in this form.

                @param fieldNum int - Index of the field number in which to search for duplicates

                @param flat bool Default False - If False, return is a map of { "duplicateKey" : lines(copy) }.
                                                 If True, return is a flat list of all duplicate lines

                @return :

                 When #flat is False:

                    dict { duplicateKeyValue[str] : lines[list<list<str>>] (copy) } -

                      This dict has the values with duplicates as the key, and a COPY of the lines as each value.

                 When #flat is True

                   lines[list<list<str>>] (copy)

                      Copies of all lines with duplicate value in #fieldNum. Duplicates will be adjacent
        '''

        # Gather the line indexes corrosponding to each key (joinField)
        #   This way, we only copy what we need, and at the end.
        keyToLineIdxs = defaultdict(list)

        for i in range(len(csvData)):
            line = csvData[i]

            fieldValue = line[fieldNum]

            keyToLineIdxs[fieldValue].append(i)

        if flat is False:
            # Assemble each key : lines(copy)
            #  for each key with more than 1 lines in its values
            ret = {}

            for key, indexes in keyToLineIdxs.items():
                if len(indexes) <= 1:
                    continue

                ret[key] = [csvData[idx][:] for idx in indexes]

        else:

            # Create a flat list of the values in keyToLineIdxs
            #   from each list of values (lines) containing more than 1 item (lines)

            ret = []

            for key, indexes in keyToLineIdxs.items():
                if len(indexes) <= 1:
                    continue

                ret += [csvData[idx][:] for idx in indexes]

        return ret

    ################################################
    #######         Private Methods          #######
    ################################################

    def __parsePattern(self):
        '''
            __parsePattern - Private method to convert a given pattern into various Rules and other attributes on this class.

            Sets variables: 
                * self.lineItems

            @return None
        '''

        # Cleanup some whitespace
        formatStr = self.formatStr.strip()
        for stripChar in OPER_CHARS:
            formatStr = re.sub('[\\' + stripChar + '][ ]+', stripChar, formatStr)

        # Some local copies of object-level variables. @see __init__ 
        currentLevels = deque()

        rules = []

        # Line items - deque< tuple< preLevels<list<tuple<str, tuple>>> 
        lineItems = deque()

        # openLineItems - A list of open line items. deque< dict< 'lineItem' : LineItem obj, 'preLineItemLevels' : tuple<level data> > >
        openLineItems = deque()

        # Track if we've ever closed a line item, after which we can't open another one.
        closedALineItem = False

        # This loop will parse from the current start of formatStr, and strip
        #  the parsed parts. When all of formatStr has been parsed, we are done.
        while formatStr:

            if formatStr[0] == '.':
                # A map access on the next quoted key
                (itemName, formatStr) = _getNextQuotedKey(formatStr[1:])

                newLevel = Level_Map(itemName)
                currentLevels.append( newLevel )

                # Ensure we don't end and that we have an open bracket
                if not formatStr:
                    raise FormatStrParseError('Unexpected end after descend into map: "%s"' %(itemName,))
                if formatStr[0] != '[':
                    raise FormatStrParseError('Expected square bracket, "[" , after descend into map: "%s". Got: %s.' %(itemName, formatStr[0]))

                # Strip bracket
                formatStr = formatStr[1:]

                continue

            elif formatStr[0] == '/':
                # A list-of-maps (list_map) access on the next quoted key
                (itemName, formatStr) = _getNextQuotedKey(formatStr[1:])


                # Ensure we don't end and that we have an open bracket
                if not formatStr:
                    raise FormatStrParseError('Unexpected end after descend into list-of-maps: "%s"' %(itemName,))
                if formatStr[0] != '[':
                    raise FormatStrParseError('Expected square bracket, "[" , after descend into list-of-maps: "%s". Got: %s.' %(itemName, formatStr[0]))

                # Strip bracket
                formatStr = formatStr[1:]

                # Extract the comparison portion ("key"="value")
                try:
                    (matchKey, formatStrNew) = _getNextQuotedKey(formatStr)
                    if not formatStrNew or formatStrNew[0] != '=':
                        raise FormatStrParseError('Expected = for "key"="value" following descend into list-of-maps "%s" at: %s' %(itemName, formatStr))
                    
                    formatStr = formatStrNew

                    (matchValue, formatStr) = _getNextQuotedKey(formatStr[1:])


                except FormatStrParseError as pe:
                    # Has a meaningful message, just raise
                    raise pe
                except Exception as e:
                    raise FormatStrParseError('Unknown exception parsing list-of-maps "%s" ( %s: %s ) at: %s' %(itemName, e.__class__.__name__, str(e), formatStr))


                newLevel = Level_ListMap(itemName, matchKey, matchValue)

                currentLevels.append( newLevel )

                continue

            elif formatStr[0] == '+':
                # Defining the line item


                (itemName, formatStrNew) = _getNextQuotedKey(formatStr[1:])

                if closedALineItem is True:
                    # Tried to open a new line item after closing another one!
                    raise FormatStrParseError('Tried to start a new line item, "%s" outside of an already closed line item. At: %s' %(itemName, formatStr) )

                formatStr = formatStrNew


                # Take all current levels and set to "preLineItemLevels".
                #  We will mark these as all the levels to walk between iterations (line items)
                preLineItemLevels = currentLevels

                # Start a fresh set of "current levels"
                currentLevels = deque()


                lineItemKey = itemName


                if not lineItems:
                    self.preLineItemRules = rules

                preRules = []
                postRules = []
                rules = preRules
                
                # We attach a fixed copy of the preLineItemLevels here,
                #   we will use a dynamic copy for the #openLineItems tracking of current open level
                #
                # Any future rules between here and the next line item will be appended to "preRules"
                #   (which starts empty, but is the same reference as "rules")
                #
                # After this line item is closed, "rules" will become a reference to "postRules"
                #  and we will start appending to that, until the next close.
                lineItem = LineItem(lineItemKey, preLineItemLevels, preRules, postRules)

                lineItems.append( lineItem )

                openLineItems.append( {'lineItem' : lineItem, 
                                       'preLineItemLevels' : copy.copy(preLineItemLevels),
                                      }
                )

                # Ensure we have bracket next
                if formatStr[0] != '[':
                    raise FormatStrParseError('Expected square bracket, "[" , after defining line item "%s". Got: %s.' %(lineItemKey, formatStr[0]))

                # Strip bracket
                formatStr = formatStr[1:]

                continue

            elif formatStr[0] == ']':
                # Closing open item

                # Simple count of all open items. Raise error if closing and nothing open

                
                if len(openLineItems) > 0:
                    if len(currentLevels) <= 0:

                        closingThisLineItem = openLineItems.pop()

                        currentLevels = closingThisLineItem['preLineItemLevels']
                        if openLineItems:
                            rules = openLineItems[-1]['lineItem'].postRules
                        else:
                            rules = self.postLineItemRules

                        closedALineItem = True
                    else:
                        # All good, remove current level
                        currentLevels.pop()

                elif len(currentLevels) > 0:
                    currentLevels.pop()
                else:
                    raise FormatStrParseError('Found closing square bracket, "]" , but no open items! At: %s' %(formatStr,))

                # Continue on, and if optional comma, strip that too.
                formatStr = formatStr[1:]
                if formatStr and formatStr[0] == ',':
                    formatStr = formatStr[1:]

                continue

            elif formatStr[0] == '"':
                # A quoted key (for printing).
                #  This is NOT an operative-prefixed quoted key
                (itemName, formatStr) = _getNextQuotedKey(formatStr)

                # Build the rule to transverse either from head -> here (pre line item),
                #   or from line item -> key to print. Note, this rule is agnostic about
                #   which of those two it is; it is generic transversal.
                rule = Rule(currentLevels, itemName, nullValue=self.nullValue, debug=self.debug)
                rules.append(rule)

                # If optional comma following this printed key, strip that too.
                if formatStr and formatStr[0] == ',':
                    formatStr = formatStr[1:]

                continue
            elif formatStr[0] in WHITESPACE_CHARS:
                # Jump to the next non-whitespace character. This allows the patterns to be written
                #  multi-line or otherwise spaced-out and readable.
                formatStr = WHITESPACE_CLEAR_RE.sub('', formatStr)

                continue
            elif formatStr[0] == '#':

                # Clear the leading comment and all whitespace, newlines, and lines which only contain
                #   comments from the cursor. (i.e. next character will be meaningful)
                formatStr = COMMENT_CLEAR_RE.sub('', formatStr)

                continue
            else:
                raise FormatStrParseError('Unhandled character: %s at: %s\n' %(formatStr[0], formatStr ))
                


        # Done formatStr-parsing loop.

        # Validate:

        PLEASE_CLOSE_STR = ' Please close (with "]") all items opened. Each "[" needs a matching close "]".'


        errorStr = 'Error: Finished parsing formatStr pattern, '

        # Support no line items
        if not lineItems:
            self.preLineItemRules = rules
#            raise FormatStrParseError(errorStr + 'No line items defined. Nothing over which to iterate.')

        if currentLevels:
            errorStr += 'There are still %d open items on the current level ("%s" is closest key that is still open)' %(len(currentLevels), currentLevels[-1].levelKey)
            if openLineItems:
                errorStr += ', and one or more open line items.'

            errorStr += PLEASE_CLOSE_STR

            raise FormatStrParseError(errorStr)

        if openLineItems:
            raise FormatStrParseError(errorStr + 'The following line items are still open: %s.%s' %(', '.join([openLineItem['lineItem'].lineItemKey for openLineItem in openLineItems]), PLEASE_CLOSE_STR))


        # Set calculated items on current object
        self.lineItems = lineItems


    def _followLineItems(self, obj, lineItem, remainingLineItems, existingFields=None):
        '''
            _followLineItems - Internal function to walk line items and extract data.

              Operates recursively

              @param obj <dict> - The current level in the json
              @param lineItem <LineItem obj> - Object of the current line item on which to operate
              @param remainingLineItems deque< LineItem obj > - The remaining sets of line items to walk. We recurse using this,
                            when this is empty we are at the most inner line item and thus we generate data.


              @return list<list<str>> - Outer list is lines, with each line being a list of each field data
        '''
        if existingFields is None:
            existingFields = []

        lines = []

        preLineItemLevels = lineItem.preLineItemLevels
        lineItemKey = lineItem.lineItemKey

        # Walk between "obj" up to the parent of the "lineItem" key
        if preLineItemLevels:
            nextObj = Rule.descendLevels(obj, preLineItemLevels, debug=self.debug)
        else:
            nextObj = obj

        if not remainingLineItems:
            # We are on the most inner, so simply extract the data into lines for return
            
            # Get the inner list of rules (note, postRules should be empty here)
            rules = lineItem.preRules + lineItem.postRules
            for item in nextObj[lineItemKey]:
                
                # Copy any previously-gathered fields into this line
                line = existingFields[:]

                # Walk each rule to each value to print
                line += [rule(item) for rule in rules]

                lines.append(line)
        else:
            # Append to the existingFields and "pre" rules prior to descend, 
            #   then recurse toward the most inner lineItem and save the results into a "newLines" variable
            #   then, if there are postRules, iterate over all those newLines and append any extra
            #     variables found at this level post-descend.
            preRules = lineItem.preRules
            postRules = lineItem.postRules
            nextLineItem = remainingLineItems.popleft()

            for item in nextObj[lineItemKey]:

                # Make a copy of the existing fields gathered prior to this level,
                #  as we don't want to pass this level's pre and posts back up
                theseExistingFields = existingFields[:]

                # If any pre-descend rules are present, add onto the theseExistingFields array before descending
                if preRules:
                    preFields = [rule(item) for rule in preRules]

                    theseExistingFields += preFields

                # Descend and gather data into newLines
                newLines = self._followLineItems(item, nextLineItem, remainingLineItems, theseExistingFields)
                if postRules:
                    postFields = [rule(item) for rule in postRules]

                    for newLine in newLines:
                        newLine += postFields

                lines += newLines

        return lines
        


# itemPattern: The regular expression to match a quoted name.
itemPattern = re.compile('^["](?P<key_name>[^"][^"]*)["]')


def _getNextQuotedKey(formatStr):
    '''
        _getNextQuotedKey - Private method which will extract the next quoted key from the formatStr,
          and return the remainder of the formatStr.

        @param formatStr <str> - The current formatStr where the next item is expected to be

        @raises ParserError - If the next item in the formatStr is not a quoted key, with a message set
          explaining further.

        @return tuple( itemName<str>, newPattern<str> ) - The item extracted, and the rest of the formatStr after item.
    '''
    if formatStr[0] != '"':
        raise FormatStrParseError('Missing expected quote character at: %s' %(formatStr,))

    matchObj = itemPattern.match(formatStr)
    if not matchObj:
        raise FormatStrParseError("Can't find end of quoted key name (missing end-quote? Key is not [a-zA-Z0-9_][^\"]*? %s" %(formatStr,))

    itemName = matchObj.groupdict()['key_name']

    # Return itemName and remainder of key after matched portion
    return (itemName, formatStr[matchObj.span()[1]:])

class FormatStrParseError(Exception):
    '''
        FormatStrParseError - Raised if there is an error in parsing the format string.

    '''
    pass

'''
    ParseError - DEPRECATED - old name for FormatStrParseError
'''
ParseError = FormatStrParseError


# These are characters with a defined operation
OPER_CHARS = (',', '.', '[', ']', '/', '+')

# These are whitespace characters. When encountered on their own
#  (i.e. not part of parsing an operation) they are stripped.
WHITESPACE_CHARS = (' ', ',', '\n', '\r', '\t')

# Pattern used to strip all whitespace starting at current position to next non-whitespace
WHITESPACE_CLEAR_RE = re.compile('^[%s]+' %(''.join(['\\' + whitespaceChar for whitespaceChar in WHITESPACE_CHARS]), ))

# Pattern to clear comments found in format str, and all whitespace and further lines
#  with only comments or whitespace until we reach a non-commented character
COMMENT_CLEAR_RE = re.compile('^([\r\n \t]*[#].*[\r\n \t]*)+')


# vim: set ts=4 sw=4 st=4 expandtab :
