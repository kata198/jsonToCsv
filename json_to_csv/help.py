'''
    Copyright (c) 2017 Timothy Savannah All Rights Reserved

    Licensed under terms of LGPLv3.


    help.py - Contains help stuff
'''

# vim: set ts=4 sw=4 st=4 expandtab :

FORMAT_HELP = '''
**Format str:**

   The format str is a series of operations and keys, plus zero or more "line item"s

**Keys:**

    Every key name listed in the format string is quoted with double-quotes.

    If the key is prefixed with an operation, it is used to REACH a value.

    If a key is NOT prefixed with an operation, it becomes a value printed.

    Unless you are using an op to change level, the quoted key should be followed
     by a comma to separate.

    A key may be anywhere before, after, or inside a line item, 
    and the keys will be output in the order they appear.

    Examples:

       "hostname"   # Print key hostname at current level

       ."hostname"[ # The . (map access) operator applied on the "hostname" key

       "hostname", "cheese" # Two keys at this current level


**Line Item:**

    A "line item" is the key iterated-over to produce each line of the csv.

    A line item is given with the '+' sign before a key.

    You may have multiple line items (so iterate over multiple keys), and you will have

      one line of output per each innermost line item found.

    You may not close a line item and then try to open another one at a different level.

    If you have no line items defined (like a single record), one csv line will be produced.

    Examples:

      +"instances"[  # For each item in the array at current level given by key 
                     #   "instances", we will generate a csv line.

      ."Something"[  # Go into key at root named 'Something'
        +"Data"[     # Iterate over each element in the array found at "Data"
        +"instances" # Iterate again over each element in the array found at "instances" within each "Data"


**Map Access:**

    The "map access" operator means to access a key at the current level

      and progresses the 'current level' to include this key access.

    A map access is given with the '.' operator before a key


    Example:

      ."Data"[   # Descend the 'current level' by the key "Data"


**List-Map Access:**

    The "list-map access" operator means to search a list of maps at the current level,
      found under the given key, until a key in that map matches a given value.

    You use the "/" operator prefix to the key, and within the square bracket define a comparitive op.

    It will stop on the FIRST match that it finds. Duplicates are not supported because it would create
      an arbitrary number of fields (and csv is fixed-field)

    For example, if you had a key "attributes" which held a bunch of maps like {"key" : ... , "value" : ... }

      and you want select the map where "key" == "color", it would look like this:

      /"attributes"["key"="color"


**Moving Between Levels:**

    You'll notice that every op descends a level, represented by being followed by a square bracket, "[".

    If you want to ascend back up to the previous level, simply close the square bracket "]".

    All open brackets must be closed before the format string ends.


**Whitespace Characters:**

    Spaces and newlines are generally ignored, and can be used to make things look nice.

**Commas:**

    Commas should be used to separate items on the same level, so after a quoted-key for printing,

     and after a close-bracket "]" if more items follow on that upper level.


**Comments:**

    You can comment directly in the format string by using the hash [ '#' ] character.

    Everything following the hash character to the end-of-line will be ignored.

    This is useful in conjunction with mulit-line patterns to document what each line is doing.

    See the "Example with inline comments" section for an example of both.


**Order:**

     Keys are printed as found left-to-right in the format string.

     You can descend into levels, back up, print keys, then descend back into those levels as many
       times as you like.


**Nulls:**

     If a value in the json map is "null" or undefined,

     an empty string is given for the value (by default, can be changed to any string).

     If there is an error following the format string to a key (like a missing key, or bad type),

       you can pass the '--debug' flag to print on stderr WHY it returned null, each time that it does.


**Case sensitive:**

      All keys are case sensitive.


**Multi-Line:**

       Because non-quoted whitespace is ignored, you can use newlines, spaces, and tabs to make long patterns more readable.


 FULL EXAMPLE:
 --------------

  ."Data"[ +"Instances"[ "hostname", /"attrs"["key"="role" "value"], /"attrs"["key"="created_at" "value", "who_set"], ."Performance"[ "cpus", "memory" ] ] ]


  Explanation:

    The given json object will first be descended by the "Data" key, where a map is expected.

    In this map, "Instances" will be the "line item", i.e. we will iterate over each item in the "Instances" list to generate each line of the csv.

    So, for each map in "Instances":

       We print the "hostname" key as the first csv element

       We descend into a list of maps under the key "attrs",
       
           search for where one of those maps has an entry "key" with the value "role",
           and we print the value of the "value" key of that map as the second csv element.

           Then, we return to previous level.

       We descend again into that list of maps under the key "attrs",

           search for where one of those maps has an entry "key" with the value "created_at",
           and we print the value of the "value" key of that map as the third csv element.
           We then print value of the "who_set" key of that same map as the fourth csv element.

           Then, we return to the previous level

       We then descend into a map under the key 'Performance'

          we print the value of the key "cpus" at this level as the fifth csv element.
          we print the value of the key "memory" at this level as the sixth csv element.

          Then, we return to the previous level

       We return to the previous level

       (we are done iterating at this point)

    We return to the previous level


**Example with inline comments:**


The following is the meant to parse the following json: https://github.com/kata198/jsonToCsv/blob/master/example_multi.json


    PARSE_STR = """
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
    """

'''
