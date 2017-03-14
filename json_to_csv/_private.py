'''
    Copyright (c) 2017 Timothy Savannah All Rights Reserved

    Licensed under terms of LGPLv3.

    Private items used in the implementation of public JsonToCsv class
'''
# vim: set ts=4 sw=4 st=4 expandtab :

import copy
import traceback
import sys

__all__ = ('Rule', 'Level', 'Level_Map', 'Level_ListMap', 'WalkNullException')

class Rule(object):
    '''
        Rule - Private object used to walk the tree.
    '''

    def __init__(self, levels, keyName, nullValue='', debug=False):
        '''
            __init__ - Construct a Rule object.

            This object should be called and passed an object to transverse and return the key found.

            @param levels - list< Level > List of objects of a subclass to "Level"

                Level types and Data:

                    * 'map' - A map access. 

                    * 'list_map' - Access a list of maps, searching for a key=value pair.
                .
            @param keyName - The key to print after transversing levels

            @param nullValue - The value to return to represent null

            @param debug <bool> Default False - If True, will print some info to stderr.
        '''
        # levels list<tuple> - The levels from parent to transverse. Copy.
        self.levels = copy.copy(levels)

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
        curLevel = obj

        for levelObj in levels:

            try:
                nextLevel = levelObj.walk(curLevel)
            except WalkNullException as walkNullE:
                if debug:
                    sys.stderr.write(walkNullE.msg + ' after descending through: %s\n' %(str(doneLevels), ))
                return None

            # TODO: Check for if nextLevel is null?

            curLevel = nextLevel

            # Append the level we just successfully transversed
            doneLevels.append( levelObj )

        # At the end - return the object reached!
        return curLevel


    def __call__(self, obj):
        '''
            __call__ - Called when this object is called. i.e. x = Rule(...)   x(myObj) <--- called here


            @param obj <dict> - The upper-most object

            @return <str / type(self.nullValue) > - Will transverse the levels and print the key associated with

               this rule. @see Rule.__init__ for more info. If it could not complete the walk or did not find the 

               final key, or the final key has a value of 'null', will return self.nullValue (as passed in __init__, default empty string).
        '''

        keyName = self.keyName
        levels = self.levels
        debug = self.debug

        doneLevels = []

        try:

            # Transverse from the object passed in down all this rule's levels,
            #  and see where we land.
            cur = Rule.descendLevels(obj, levels, debug, doneLevels)

            if cur is None:
                # We could not walk based on the format pattern.
                #  TODO: Maybe make this (unreachable) configurable different from null?
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
            exc_info = sys.exc_info()
            if debug:
                sys.stderr.write('Returning null because unknown exception. %s: %s\n' %(e.__class__.__name__, str(e)))
                traceback.print_exception(*exc_info, file=sys.stderr)

            return self.nullValue


class WalkNullException(Exception):
    '''
        WalkNullException - Raised when a Level cannot walk down (reality doesn't match expected format).

        contains 'msg' attribute which contains the message

        Private
    '''
    
    def __init__(self, msg=''):
        Exception.__init__(self, msg)

        self.msg = msg

class Level(object):
    '''
        Level - Base class of any level-walk operations.
        
        Does not itself hold implement of walk method.

        For the subclasses, calling obj.walk(level) will perform the walk from level -> newLevel, and return newLevel if found.

          If newLevel could not be reached, WalkNullException will be raised with a message (.msg) defined to be the reason why (for debug purposes)

        Private
    '''


    __slots__ = ('levelKey', )

    levelType = 'undefined'

    def __init__(self, levelKey):
        '''
            __init__ - Create a Level object.

            @param levelKey <str> - The key at which we will descend into to get to the next level
        '''
        self.levelKey = levelKey

    def walk(self, curLevel):
        '''
            walk - Walk from the current level (#curLevel) and return the level reached.

            @param curLevel <dict> - The starting level

            @return <dict> - The landing level

            @raises WalkNullException - If the walk could not be completed
        '''
        raise NotImplementedError('Level.walk is not implemented! Use a subclass!')


    def __str__(self):
        return '%s( %s )' %(self.__class__.__name__, ', '.join(['%s = "%s"' %(attrName, getattr(self, attrName)) for attrName in self.__class__.__slots__]))

    __repr__ = __str__


class Level_Map(Level):
    '''
        Level_Map - A type of Level access which simply accesses a key on a map.

        @see Level

        Private
    '''

    __slots__ = Level.__slots__

    levelType = 'map'

    def __init__(self, levelKey):
        '''
            __init__ - Create a Level_Map object

            @param levelKey <str> - The string on which to access
        '''
        Level.__init__(self, levelKey)

    def walk(self, curLevel):
        '''
            walk - Walk from the current level accessing a key, and return that as the next level

            @see Level.walk

            @param curLevel <dict> - Current level
            
            @return <dict> - The landing level

            @raises WalkNullException - If the key does not exist, or does not point to a map
        '''
        levelKey = self.levelKey

        if levelKey not in curLevel:
            raise WalkNullException('Returning null because map key="%s" is not contained' %(levelKey,))

        ret = curLevel[levelKey]

        if not isinstance(ret, dict):
            raise WalkNullException('Returning null because map key="%s" does not point to a map' %(levelKey, ))

        return curLevel[levelKey]

class Level_ListMap(Level):
    '''
        Level_ListMap - A Level that searches a list of maps for a specific key : value

        Like:

       "MyKey" : [{
             "name" : "Something",
             "value" : "x"
           },
           {
             "name" : "Blah",
             "value" : "y"
           }
       ]

        If we wanted to descend into the one with name equal to "Something", we would have:

           ListMap("MyKey", "name", "Something")

        or in the format language, 

           /"MyKey"["name"="Something"

        @see Level

        Private
    '''

    __slots__ = tuple(list(Level.__slots__) + ['matchKey', 'matchValue'])

    levelType = 'list_map'

    def __init__(self, levelKey, matchKey, matchValue):
        '''
            __init__ - Create a Level_ListMap object

            @param levelKey <str> - The key with which to find this list-of-maps

            @param matchKey <str> - The key we will check against in each map

            @param matchValue<str> - The value we are looking for in #matchKey to select that map
        '''
        Level.__init__(self, levelKey)

        self.matchKey = matchKey
        self.matchValue = matchValue

    def walk(self, curLevel):
        '''
            walk - Walk from the current level (#curLevel) to the next level and return that next level

            @param curLevel <dict> - The current level

            @return <dict> - The level reached

            @throws WalkNullException if:

               1. #curLevel does not contain a key matching #levelKey
               2. The result of #curLevel[#levelKey] is not a list or contains items other than maps
               3. No match found

        '''
        (levelKey, matchKey, matchValue) = (self.levelKey, self.matchKey, self.matchValue)

        if levelKey not in curLevel:
            # error, the specified key for this list-map was not found
            raise WalkNullException('Returning null because list_map key="%s" is not contained' % (levelKey, ))


        found = False

        if not isinstance(curLevel[levelKey], (list, tuple)):
            raise WalkNullException('Returning null because list_map key="%s" is not a list' % (levelKey, ))

        for theMap in curLevel[levelKey]:

            if not isinstance(theMap, dict):
                raise WalkNullException('Returning null because list_map key="%s" is not a list of only maps' % (levelKey, ))

            if matchKey not in theMap:
                # The specified key was not in this map, move on
                continue

            if theMap[matchKey] == matchValue:
                # The specified key matches the value, this is the one!
                return theMap

        # If we got here, we didn't find a match..
        raise WalkNullException('Returning null because list_map key="%s" did not contain a map where "%s" = "%s"' % (levelKey, matchKey, matchValue))


class LineItem(object):
    '''
        LineItem - an object representing a "Line Item", i.e. a key and associated information on which to iterate.

        Private
    '''

    __slots__ = ('lineItemKey', 'preLineItemLevels', 'preRules', 'postRules')

    def __init__(self, lineItemKey, preLineItemLevels, preRules=None, postRules=None):
        '''
            Construct a LineItem object.

            @param lineItemKey <str> - The key on which to iterate

            @param preLineItemLevels list<levels> - The levels to iterate between previous object and here

            @param preRules list<Rule> - This is a list of the rules to follow BEFORE transversing to the next line item.
                You should keep reference to this and append accordingly.

            @param postRules list<Rule> - This is a list of the rules to follow AFTER returning from the following line item.
                You should keep reference to this and append accordingly.
         '''
        self.lineItemKey = lineItemKey

        self.preLineItemLevels = preLineItemLevels

        if preRules is None:
            preRules = []
        self.preRules = preRules

        if postRules is None:
            postRules = []
        self.postRules = postRules


# vim: set ts=4 sw=4 st=4 expandtab :
