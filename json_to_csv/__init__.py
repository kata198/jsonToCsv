'''
    Copyright (c) 2017 Timothy Savannah All Rights Reserved

    Licensed under terms of LGPLv3.

    json_to_csv - Module for converting json data to csv data, and various supplementry methods.

    TODO: Does not handle double-quote embedded in data
    TODO: Does not handle commas embedded in data
'''

import json
import sys
import re


class ParseError(Exception):
    '''
        ParseError - Raised if there is an error in parsing the format string.

        TODO: Better name.
    '''
    pass


itemPattern = re.compile('^["](?P<key_name>[^"][^"]*)["]')


def _getNextQuotedKey(pattern):
    '''
        _getNextQuotedKey - Private method which will extract the next quoted key from the pattern,
          and return the remainder of the pattern.

        @param pattern <str> - The current pattern where the next item is expected to be

        @raises ParserError - If the next item in the pattern is not a quoted key, with a message set
          explaining further.

        @return tuple( itemName<str>, newPattern<str> ) - The item extracted, and the rest of the pattern after item.
    '''
    if pattern[0] != '"':
        raise ParseError('Missing expected quote character at: %s' %(pattern,))
    matchObj = itemPattern.match(pattern)
    if not matchObj:
        raise ParseError("Can't find end of quoted key name (missing end-quote? Key is not [a-zA-Z0-9_][^\"]*? %s" %(pattern,))

    itemName = matchObj.groupdict()['key_name']

    return (itemName, pattern[matchObj.span()[1]:])



class JsonToCsv(object):
    '''
        JsonToCsv - Public class containing methods for dealing with converting
            Json to csv data, merging data, etc

    '''

    # These are characters with a defined operation
    OPER_CHARS = (',', '.', '[', ']', '/', '+')

    def __init__(self, pattern, nullValue='', debug=False):
        '''
            __init__ - Create a JsonToCsv object.

            @param pattern <str> - The format pattern for the json data to be converted.

            @param nullValue <str> Default empty string - The value to assign to a "null" result.

            @param debug <bool> Default False - If True, will output some debug data on stderr.
        '''

        # format pattern
        self.pattern = pattern

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

        pattern = self.pattern[:].strip()
        for stripChar in self.OPER_CHARS:
            pattern = re.sub('[\\' + stripChar + '][ ]+', stripChar, pattern)

        currentLevels = []

        rules = []

        preLineItemLevels = []

        preLineItemIn = 0

        lineItem = None

        lineItemOpen = False

        while pattern:
            if pattern[0] == '.':
                (itemName, pattern) = _getNextQuotedKey(pattern[1:])
                currentLevels.append( ( 'map', (itemName, ) ) )

                if not pattern:
                    raise ParseError('Unexpected end after descend into map: "%s"' %(itemName,))
                if pattern[0] != '[':
                    raise ParseError('Expected square bracket, "[" , after descend into map: "%s". Got: %s.' %(itemName, pattern[0]))
                pattern = pattern[1:]
                continue

            elif pattern[0] == '/':
                (itemName, pattern) = _getNextQuotedKey(pattern[1:])


                if not pattern:
                    raise ParseError('Unexpected end after descend into list-of-maps: "%s"' %(itemName,))
                if pattern[0] != '[':
                    raise ParseError('Expected square bracket, "[" , after descend into list-of-maps: "%s". Got: %s.' %(itemName, pattern[0]))
                pattern = pattern[1:]

                patternBefore = pattern[:]
                try:
                    (matchKey, pattern) = _getNextQuotedKey(pattern)
                    if not pattern or pattern[0] != '=':
                        raise ParseError('Expected = for "key"="value" following descend into list-of-maps "%s" at: %s' %(itemName, patternBefore))

                    (matchValue, pattern) = _getNextQuotedKey(pattern[1:])
#                    if not pattern or pattern[0] != '[':
#                        raise ParseError('Expected square bracket, "[" , after comparison for list-of-maps "%s" at: %s' %(itemName, pattern))
                except ParseError as pe:
                    raise pe
                except Exception as e:
                    raise ParseError('Unknown exception parsing list-of-maps "%s" ( %s: %s ) at: %s' %(itemName, e.__class__.__name__, str(e), pattern))

#                pattern = pattern[1:]

                currentLevels.append( ('list_map', (itemName, matchKey, matchValue) ) )

#+"instances"["key1", ."subMap"["map1", "map2"], /"sub"["subkey1"="subval1"["subkey2"]], "key2"]

                continue

            elif pattern[0] == '+':
                if lineItem:
                    raise ParseError('Multiple line items detected. Already had "%s", and found a new one at: %s' %(lineItem, pattern))

                preLineItemLevels = currentLevels[:]
                preLineItemIn = len(preLineItemLevels)

                currentLevels = []

                if rules:
                    raise ParseError('Keys are not allowed before the line item is defined.')

                (itemName, pattern) = _getNextQuotedKey(pattern[1:])

                lineItem = itemName

                if pattern[0] != '[':
                    raise ParseError('Expected square bracket, "[" , after defining line item "%s". Got: %s.' %(lineItem, pattern[0]))
                pattern = pattern[1:]

                lineItemOpen = True
                continue

            elif pattern[0] == ']':
                if not currentLevels:
                    if preLineItemIn > 0:
                        preLineItemIn -= 1
                    elif lineItemOpen:
                        lineItemOpen = False
                    else:
                        raise ParseError('Found closing square bracket, "]" , but no open items! At: %s' %(pattern,))
                else:
                    currentLevels = currentLevels[:-1]

                pattern = pattern[1:]
                if pattern and pattern[0] == ',':
                    pattern = pattern[1:]
                continue

            elif pattern[0] == '"':
                (itemName, pattern) = _getNextQuotedKey(pattern)

                rule = Rule(currentLevels, itemName, nullValue=self.nullValue, debug=self.debug)
                rules.append(rule)

                if pattern and pattern[0] == ',':
                    pattern = pattern[1:]
                continue
            elif pattern[0] in (',', ' ', '\n', '\r', '\t'):
                pattern = pattern[1:]
                continue
            else:
                sys.stderr.write('Unhandled character: %s\n' %(pattern[0], ))


        if not lineItem:
            raise ParseError('No line item defined.')

        if currentLevels or preLineItemIn:
            raise ParseError('Finished parsing pattern, there are still %d levels open ( missing end square bracket "]" )' %(len(currentLevels) + preLineItemIn, ))

        if lineItemOpen:
            raise ParseError('Finished parsing pattern, line item "%s" is still open ( missing end square bracket "]" )' %(lineItem, ))

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
        if not isinstance(data, dict):
            obj = json.loads(data)
        else:
            obj = data

        if self.preLineItemLevels:
            obj = Rule.descendLevels(obj, self.preLineItemLevels, debug=self.debug)

        rules = self.rules

        lines = []

        for item in obj[self.lineItem]:
            line = []
            for rule in rules:
                line.append(rule(item))
            lines.append(','.join(line))

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
        if not isinstance(data, dict):
            obj = json.loads(data)
        else:
            obj = data

        if self.preLineItemLevels:
            obj = Rule.descendLevels(obj, self.preLineItemLevels, debug=self.debug)

        rules = self.rules

        lines = []

        for item in obj[self.lineItem]:
            line = []
            for rule in rules:
                line.append(rule(item))
            lines.append(line)

        return lines

    @staticmethod
    def dataToStr(csvData):
        '''
            dataToStr - Convert a list of lists of csv data to a string.

            @param csvData list<list> - A list of lists, first list is lines, inner-list are values.

              This is the data returned by JsonToCsv.extractData

            @return str - csv data
        '''
        if not isinstance(csvData, list) or not isinstance(csvData[0], list):
            raise ValueError('csvData is not a list-of-lists. dataToStr is meant to convert the return of "extractData" method to csv data.')

        lines = [','.join(items) for items in csvData]

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
        '''
        if not isinstance(csvData1, list) or not isinstance(csvData1[0], list):
            raise ValueError('csvData1 is not a list of lists, as expected. Use extractData to gather lists of lists for this method.')
        if not isinstance(csvData2, list) or not isinstance(csvData2[0], list):
            raise ValueError('csvData2 is not a list of lists, as expected. Use extractData to gather lists of lists for this method.')


        csvData1Map = {}

        csvData2Keys = set()

        onlyData1 = []
        onlyData2 = []
        combinedData = []

        for data in csvData1:
            data = data[:]
            joinFieldData = data[joinFieldNum1]
            if joinFieldData in csvData1Map:
                raise KeyError('Duplicate data in joinField %d on csvData1: %s' %(joinFieldNum1, joinFieldData))
            csvData1Map[joinFieldData] = data


        for data in csvData2:
            data = data[:]
            joinFieldData = data[joinFieldNum2]
            if joinFieldData in csvData2Keys:
                raise KeyError('Duplicate data in joinField %d on csvData2: %s' %(joinFieldNum2, joinFieldData))
            csvData2Keys.add(joinFieldData)

            if joinFieldData in csvData1Map:
                newData = data[ :joinFieldNum2] + data[joinFieldNum2 + 1 :]
                combinedData.append(csvData1Map[joinFieldData] + newData)
            else:
                onlyData2.append(data)

        onlyData1Keys = set(csvData1Map.keys()).difference(csvData2Keys)
        for key in onlyData1Keys:
            onlyData1.append(csvData1Map[key])

        return (combinedData, onlyData1, onlyData2)


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

        self.levels = levels[:]
        self.keyName = keyName

        self.debug = debug

        self.nullValue = nullValue


    @staticmethod
    def descendLevels(obj, levels, debug=False, doneLevels=None):
        '''
            descendLevels - Takes an object and descends a series of levels, returning the final object reached.

            @param obj <dict> - The starting object

            @param levels <list<tuple>> - Levels to transverse. @see Rule.__init__ for more info

            @param debug <bool> Default False - If True, will print some info to stderr

            @param doneLevels <None/list> Default None, if you provide a list, it will contain all the levels transversed before stopping.

                If you get a return of 'None' (can't transverse all levels), this will show you where it stopped.

            @return <dict/None> - If could transverse successfully, will return the object reached.

                If it could not, will return None. @see doneLevels
        '''
        if doneLevels is None:
            doneLevels = []

        cur = obj

        for levelType, data in levels:
            if levelType == 'map':

                (levelKey, ) = data

                if levelKey not in cur:
                    if debug:
                        sys.stderr.write('Returning null because map key="%s" is not contained after descending through: %s\n' %(levelKey, str(doneLevels)) )

                    return None

                cur = cur[levelKey]

            elif levelType == 'list_map':

                (levelKey, matchKey, matchValue) = data

                if levelKey not in cur:
                    if debug:
                        sys.stderr.write('Returning null because list_map key="%s" is not contained after descending through: %s\n' %(levelKey, str(doneLevels)) )

                    return None

                found = False

                # TODO: Make sure this is a list
                for theMap in cur[levelKey]:
                    if matchKey not in theMap:
                        continue

                    if theMap[matchKey] == matchValue:
                        cur = theMap
                        found = True
                        break

                if found is False:
                    if debug:
                        sys.stderr.write('Returning null because list_map key="%s" did not contain a map where "%s" = "%s" after descending through: %s\n' %(levelKey, matchKey, matchValue, str(doneLevels)) )

                    return None


            doneLevels.append( (levelType, data) )

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

        doneLevels = []

        try:

            debug = self.debug


            cur = Rule.descendLevels(obj, levels, debug, doneLevels)

            if cur is None:
                return self.nullValue


            if keyName not in cur:
                if debug:
                    sys.stderr.write('Returning null because no key "%s" exists after descending through: %s\n' %(keyName, str(doneLevels)))
                return self.nullValue

            if cur[keyName] is None:
                if debug:
                    sys.stderr.write('Returning null because keyname "%s" has value "null" after descending through: %s\n' %(keyName, str(doneLevels)))
                return self.nullValue

            return str(cur[keyName])

        except Exception as e:
            if debug:
                sys.stderr.write('Returning null because unknown exception. %s: %s\n' %(e.__class__.__name__, str(e)))

            return self.nullValue

