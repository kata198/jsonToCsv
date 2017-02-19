'''
    Copyright (c) 2017 Timothy Savannah All Rights Reserved

    Licensed under terms of LGPLv3.

    json_to_csv - Module for converting json data to csv data, and various supplementry methods.

    TODO: Does not handle double-quote embedded in data
    TODO: Does not handle commas embedded in data
'''

# vim: set ts=4 sw=4 st=4 expandtab :

import json
import sys
import re

from collections import defaultdict


class ParseError(Exception):
    '''
        ParseError - Raised if there is an error in parsing the format string.

        TODO: Better name.
    '''
    pass


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
        raise ParseError('Missing expected quote character at: %s' %(formatStr,))

    matchObj = itemPattern.match(formatStr)
    if not matchObj:
        raise ParseError("Can't find end of quoted key name (missing end-quote? Key is not [a-zA-Z0-9_][^\"]*? %s" %(formatStr,))

    itemName = matchObj.groupdict()['key_name']

    # Return itemName and remainder of key after matched portion
    return (itemName, formatStr[matchObj.span()[1]:])



class JsonToCsv(object):
    '''
        JsonToCsv - Public class containing methods for dealing with converting
            Json to csv data, merging data, etc

    '''

    # These are characters with a defined operation
    OPER_CHARS = (',', '.', '[', ']', '/', '+')

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

        # preLineItemLevels - A list of "levels" that must be walked to
        #   get to the line item. Each "level" is a tuple of ( type<str> , data<tuple> )
        self.preLineItemLevels = None

        # lineItem - The key of the item to be iterated over
        self.lineItem = None

        # rules - A list of Rule objects, which are executed on the lineItem to extract the results.
        self.rules = None

        # Fill the private attributes above
        self.__parsePattern()


    def __parsePattern(self):
        '''
            __parsePattern - Private method to convert a given pattern into various Rules and other attributes on this class.

            Sets variables: 
                * self.preLineItemLevels
                * self.lineItem
                * self.rules

            @return None
        '''

        # Cleanup some whitespace
        formatStr = self.formatStr[:].strip()
        for stripChar in self.OPER_CHARS:
            formatStr = re.sub('[\\' + stripChar + '][ ]+', stripChar, formatStr)

        # Some local copies of object-level variables. @see __init__ 
        currentLevels = []

        rules = []

        preLineItemLevels = []

        # Number of pre-lineItem levels we were in (for counting)
        preLineItemIn = 0

        lineItem = None

        # If the lineItem has been closed. (NOTE: Not really, just a +1 for now, see below)
        lineItemOpen = False

        # This loop will parse from the current start of formatStr, and strip
        #  the parsed parts. When all of formatStr has been parsed, we are done.
        while formatStr:

            if formatStr[0] == '.':
                # A map access on the next quoted key
                (itemName, formatStr) = _getNextQuotedKey(formatStr[1:])
                currentLevels.append( ( 'map', (itemName, ) ) )

                # Ensure we don't end and that we have an open bracket
                if not formatStr:
                    raise ParseError('Unexpected end after descend into map: "%s"' %(itemName,))
                if formatStr[0] != '[':
                    raise ParseError('Expected square bracket, "[" , after descend into map: "%s". Got: %s.' %(itemName, formatStr[0]))

                # Strip bracket
                formatStr = formatStr[1:]

                continue

            elif formatStr[0] == '/':
                # A list-of-maps (list_map) access on the next quoted key
                (itemName, formatStr) = _getNextQuotedKey(formatStr[1:])


                # Ensure we don't end and that we have an open bracket
                if not formatStr:
                    raise ParseError('Unexpected end after descend into list-of-maps: "%s"' %(itemName,))
                if formatStr[0] != '[':
                    raise ParseError('Expected square bracket, "[" , after descend into list-of-maps: "%s". Got: %s.' %(itemName, formatStr[0]))

                # Strip bracket
                formatStr = formatStr[1:]

                formatStrBefore = formatStr[:]

                # Extract the comparison portion ("key"="value")
                try:
                    (matchKey, formatStr) = _getNextQuotedKey(formatStr)
                    if not formatStr or formatStr[0] != '=':
                        raise ParseError('Expected = for "key"="value" following descend into list-of-maps "%s" at: %s' %(itemName, formatStrBefore))

                    (matchValue, formatStr) = _getNextQuotedKey(formatStr[1:])


                except ParseError as pe:
                    # Has a meaningful message, just raise
                    raise pe
                except Exception as e:
                    raise ParseError('Unknown exception parsing list-of-maps "%s" ( %s: %s ) at: %s' %(itemName, e.__class__.__name__, str(e), formatStr))


                currentLevels.append( ('list_map', (itemName, matchKey, matchValue) ) )

                continue

            elif formatStr[0] == '+':
                # Defining the line item


                if lineItem:
                    raise ParseError('Multiple line items detected. Already had "%s", and found a new one at: %s' %(lineItem, formatStr))

                # Take all current levels and set to "preLineItemLevels".
                #  Later, we will transverse these before we start iterating, and we only iterate
                #  FROM this line item.
                #
                # TODO: Support multiple line items? Change to 'preFirstLineItem', 
                #   and then a list of levels and rules to iterate between?
                preLineItemLevels = currentLevels[:]
                preLineItemIn = len(preLineItemLevels)

                currentLevels = []

                if rules:
                    raise ParseError('Keys are not allowed before the line item is defined.')

                # Extract and assign the line item name
                (itemName, formatStr) = _getNextQuotedKey(formatStr[1:])

                lineItem = itemName
                lineItemOpen = True

                # Ensure we have bracket next
                if formatStr[0] != '[':
                    raise ParseError('Expected square bracket, "[" , after defining line item "%s". Got: %s.' %(lineItem, formatStr[0]))

                # Strip bracket
                formatStr = formatStr[1:]

                continue

            elif formatStr[0] == ']':
                # Closing open item

                # Simple count of all open items. Raise error if closing and nothing open
                #
                #  TODO: If support multiple line items, may need to convert this to actually
                #   a stack to keep track of WHAT is closing moreso than we do
                #   ( i.e. integrate the preLineItem and lineItemOpen into the tracked stack with currentLevels )
                if not currentLevels:
                    if preLineItemIn > 0:
                        preLineItemIn -= 1
                    elif lineItemOpen:
                        lineItemOpen = False
                    else:
                        raise ParseError('Found closing square bracket, "]" , but no open items! At: %s' %(formatStr,))
                else:
                    # All good, remove current level
                    currentLevels = currentLevels[:-1]

                # Continue on, and if optional comma, strip that too.
                formatStr = formatStr[1:]
                if formatStr and formatStr[0] == ',':
                    formatStr = formatStr[1:]

                continue

            elif formatStr[0] == '"':
                # A quoted key (for printing).
                #  NOTE: This is NOT an operative-prefixed quoted key
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
            elif formatStr[0] in (',', ' ', '\n', '\r', '\t'):
                # I don't like that this rule contains comma, because really it means we would parse
                #  something like: +"something"[,,,,,,,,"key"] as valid, which it is... but.... sigh..
                #  anyway, better just be safe and strip off meaningless characters.
                #
                # The newline and tab and space portions mean these formatStrs can really be multi-line
                formatStr = formatStr[1:]

                continue
            else:
                sys.stderr.write('Unhandled character: %s\n' %(formatStr[0], ))


        # Done formatStr-parsing loop.

        # Validate:

        if not lineItem:
            raise ParseError('No line item defined.')

        if currentLevels or preLineItemIn:
            raise ParseError('Finished parsing formatStr pattern, there are still %d levels open ( missing end square bracket "]" )' %(len(currentLevels) + preLineItemIn, ))

        if lineItemOpen:
            raise ParseError('Finished parsing formatStr pattern, line item "%s" is still open ( missing end square bracket "]" )' %(lineItem, ))

        # Set calculated items on current object
        self.rules = rules
        self.lineItem = lineItem

        self.preLineItemLevels = preLineItemLevels



    def convertToCsv(self, data, asList=False):
        '''
            convertToCsv - Convert given data to csv.

            @param data <string/dict> - Either a string of json data, or a dict
            @param asList <bool> Default False - If True, will return a list of the lines (as strings), otherwise will just return a string.

            @return <list/str> - see "asList" param above.
        '''

        # Get data in the right format
        if not isinstance(data, dict):
            obj = json.loads(data)
        else:
            obj = data

        # Transverse the pre-line item levels. We will iterate from here.
        #   All rules after lineItem is defined start from lineItem
        if self.preLineItemLevels:
            obj = Rule.descendLevels(obj, self.preLineItemLevels, debug=self.debug)

        rules = self.rules

        # lines - For return
        lines = []

        # Iterate over the lineItem
        for item in obj[self.lineItem]:
            line = []
            # Walk each rule to each value to print
            for rule in rules:
                line.append(rule(item))
            # Append csv-data for this line
            lines.append(','.join(line))

        # If asList, we return a list of strings (lines), otherwise, we return a string
        if asList:
            return lines

        return '\n'.join(lines)


    def extractData(self, data):
        '''
            extractData - Return a list of lists. The outer list represents lines, the inner list data points.

                e.x.  returnData[0] is first line,  returnData[0][2] is first line third data point.

                @param data <string/dict> - Either a string of JSON data, or a dict.

                @return list<list<str>> - List of lines, each line containing a list of datapoints.
        '''
        # TODO: copied from above

        # Get data in right format
        if not isinstance(data, dict):
            obj = json.loads(data)
        else:
            obj = data

        # Transverse the pre-line item levels. We will iterate from here.
        #   All rules after lineItem is defined start from lineItem
        if self.preLineItemLevels:
            obj = Rule.descendLevels(obj, self.preLineItemLevels, debug=self.debug)

        rules = self.rules

        # lines - for return, list<list>(strs)
        lines = []

        for item in obj[self.lineItem]:
            line = []
            # Walk each rule to each value to print
            for rule in rules:
                line.append(rule(item))
            # Append this list of values, as a line
            lines.append(line)

        return lines

    @staticmethod
    def dataToStr(csvData, separator=','):
        '''
            dataToStr - Convert a list of lists of csv data to a string.

            @param csvData list<list> - A list of lists, first list is lines, inner-list are values.
            @param separator <str> - Default ',' this is the separator used between fields (i.e. would be a tab in TSV format)

              This is the data returned by JsonToCsv.extractData

            @return str - csv data
        '''
        # TODO: Maybe support other formats? We would have to handle converting csv -> list<list> though,
        #  which is probably outside the scope of this module.
        if not isinstance(csvData, list) or not isinstance(csvData[0], list):
            raise ValueError('csvData is not a list-of-lists. dataToStr is meant to convert the return of "extractData" method to csv data.')

        # Each line is the comma-joining (or whatever #separator is) of its values
        lines = [separator.join(items) for items in csvData]

        return '\n'.join(lines)

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
            # Copy data (list-by-ref)
            data = data[:]

            joinFieldData = data[joinFieldNum1]
            # If duplicate found we cannot continue the join
            if joinFieldData in csvData1Map:
                raise KeyError('Duplicate data in joinField %d on csvData1: %s' %(joinFieldNum1, joinFieldData))

            csvData1Map[joinFieldData] = data


        # Extract the "joinKey" from csvData2, and merge if possible
        for data in csvData2:
            # Copy data (list-by-ref)
            data = data[:]

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
                onlyData2.append(data)

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
            # Copy data (list-by-ref)
            data = data[:]

            joinFieldData = data[joinFieldNum1]

            csvData1Map[joinFieldData].append(data)


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

            allData = []

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



class Rule(object):
    '''
        Rule - Private object used to walk the tree.
    '''

    def __init__(self, levels, keyName, nullValue='', debug=False):
        '''
            __init__ - Construct a Rule object.

            This object should be called and passed an object to transverse and return the key found.

            @param levels - List of tuples representing levels to transverse. (levelType<str>, levelData<tuple)

                Level types and Data:

                    * 'map' - A map access. 

                        Data is (<str>, )

                            - first element is key to access.

                    * 'list_map' - Access a list of maps, searching for a key=value pair.

                        Data is (<str>, <str>, <str>)

                            - First element is key to access
                            - Second element is key to search for in the list of maps
                            - Third element is the value the 'matched' key will hold.

                .
            @param keyName - The key to print after transversing levels

            @param nullValue - The value to return to represent null

            @param debug <bool> Default False - If True, will print some info to stderr.
        '''

        # levels list<tuple> - The levels from parent to transverse. Copy.
        self.levels = levels[:]

        # keyName <str> - The final keyname to print 
        self.keyName = keyName

        # debug flag - bool
        self.debug = debug

        # nullValue - string to represent a "null" or missing field.
        #  TODO: Maybe null and "unreachable" should be configurable to be different?
        self.nullValue = nullValue


    @staticmethod
    def descendLevels(obj, levels, debug=False, doneLevels=None):
        '''
            descendLevels - Takes an object and descends a series of levels, returning the final object reached.

               "Walk" from #obj down #levels and return the resulting object.

            @param obj <dict> - The starting object

            @param levels <list<tuple>> - Levels to transverse. @see Rule.__init__ for more info

            @param debug <bool> Default False - If True, will print some info to stderr

            @param doneLevels <None/list> Default None, if you provide a list, it will contain all the levels transversed before stopping.

                If you get a return of 'None' (can't transverse all levels), this will show you where it stopped.

            @return <dict/None> - If could transverse successfully, will return the object reached.

                If it could not, will return None. @see doneLevels
        '''

        # If they didn't provide a #doneLevels, make a local list
        if doneLevels is None:
            doneLevels = []

        # Start at the #obj
        cur = obj

        for levelType, data in levels:
            if levelType == 'map':
                # map - Access just a single key on this level

                (levelKey, ) = data

                if levelKey not in cur:
                    # Error, the requested key was not at this level
                    if debug:
                        sys.stderr.write('Returning null because map key="%s" is not contained after descending through: %s\n' %(levelKey, str(doneLevels)) )

                    return None

                cur = cur[levelKey]

            elif levelType == 'list_map':
                # list_map - Access a list of maps based on a key at this level,
                #   and look for a specific key=value pair

                (levelKey, matchKey, matchValue) = data

                if levelKey not in cur:
                    # error, the specified key for this list-map was not found
                    if debug:
                        sys.stderr.write('Returning null because list_map key="%s" is not contained after descending through: %s\n' %(levelKey, str(doneLevels)) )

                    return None

                found = False

                # TODO: Make sure this is a list, and make sure each entry is a dict.
                for theMap in cur[levelKey]:

                    if matchKey not in theMap:
                        # The specified key was not in this map, move on
                        continue

                    if theMap[matchKey] == matchValue:
                        # The specified key matches the value, this is the one!
                        cur = theMap
                        found = True
                        break

                # Check if we found out match
                if found is False:
                    if debug:
                        sys.stderr.write('Returning null because list_map key="%s" did not contain a map where "%s" = "%s" after descending through: %s\n' %(levelKey, matchKey, matchValue, str(doneLevels)) )

                    return None

            # Append the level we just successfully transversed
            doneLevels.append( (levelType, data) )

        # At the end - return the object reached!
        return cur


    def __call__(self, obj):
        '''
            __call__ - Called when this object is called. i.e. x = Rule(...)   x(myObj) <--- called here


            @param obj <dict> - The upper-most object

            @return <str / type(self.nullValue) > - Will transverse the levels and print the key associated with

               this rule. @see Rule.__init__ for more info. If it could not complete the walk or did not find the 

               final key, or the final key has a value of 'null', will return self.nullValue (as passed in __init__, default empty string).
        '''

        keyName = self.keyName
        levels = self.levels[:]
        debug = self.debug

        doneLevels = []

        try:

            # Transverse from the object passed in down all this rule's levels,
            #  and see where we land.
            cur = Rule.descendLevels(obj, levels, debug, doneLevels)

            if cur is None:
                # We could not walk based on the format pattern.
                #  TODO: Maybe make this configurable different from null?
                return self.nullValue


            # We walked to the end, now look for the key requested to print
            if keyName not in cur:
                if debug:
                    sys.stderr.write('Returning null because no key "%s" exists after descending through: %s\n' %(keyName, str(doneLevels)))
                return self.nullValue

            # Check if the value is "null" in json (None in python)
            if cur[keyName] is None:
                if debug:
                    sys.stderr.write('Returning null because keyname "%s" has value "null" after descending through: %s\n' %(keyName, str(doneLevels)))
                return self.nullValue

            # All good, return a string of the value!
            #   TODO: Make sure this is not a list type
            #   TODO: Make sure to escape any commas
            return str(cur[keyName])

        except Exception as e:
            # Unknown/unexpected exception
            if debug:
                sys.stderr.write('Returning null because unknown exception. %s: %s\n' %(e.__class__.__name__, str(e)))

            return self.nullValue


