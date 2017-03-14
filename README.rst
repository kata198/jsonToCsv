jsonToCsv
=========

Converts json data to csv via a meta language (format string)

The output csv is RFC 4180 compliant by default (behaviour can be changed with options).


The Problem
-----------

The problem with converting json to csv is that json is a dynamic, multi-typed, nested format. Csv on the other hand is a fixed single-type format.

JsonToCsv solves this by defining a meta language (format string) which can be used to define repeatable and fixed-format steps, allowing the flattening of the wide json domain space into the slim csv space.



Format String
=============

Because csv is a fixed-format field and json is free-format, a meta language had to be developed to describe the various movements to find and output values into a fixerd format. This section describes that format.

**Format str:**

	The format str is a series of operations and keys, plus zero or more "line item"s.

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

	You may not close a line item and then try to open another one at another level.

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

**Comments:**

	You can comment directly in the format string by using the hash [ '#' ] character.

	Everything following the hash character to the end-of-line will be ignored.

	This is useful in conjunction with mulit-line patterns to document what each line is doing.

	See the "Example with inline comments" section for an example of both.

Commas:

	Commas should be used to separate items on the same level, so after a quoted-key for printing,
	and after a close-bracket "]" if more items follow on that upper level.

Order:

	Keys are printed as found left-to-right in the format string.

	You can descend into levels, back up, print keys, then descend back into those levels as many
	  times as you like.


Nulls:

	 If a value in the json map is "null" or undefined,

	 an empty string is given for the value (by default, can be changed to any string).

	 If there is an error following the format string to a key (like a missing key, or bad type),

	 you can pass the '--debug' flag to print on stderr WHY it returned null, each time that it does.

Case sensitive:

	All keys are case sensitive.

Multi-Line:

	Because non-quoted whitespace is ignored, you can use newlines, spaces, and tabs to make long patterns more readable.


Tool
====

This module ships with a script, jsonToCsv, which can be used standalone to perform the operations.

	Usage: jsonToCsv [format str]

		Formats a json string ( delivered via stdin ) to csv, based on provided format str.

		
		Options:


			--null-value=XXX          Use "XXX" instead of an empty string as the null value

			--quote-fields=X          Defaults to "Smart quoting", i.e. fields will be quoted

										according to RFC 4180 as-needed. You can specify "true" or "false"

										here explicitly to force a behaviour



			--help                    Show this message

			--format-help             Show usage on format string representation


			--version                 Print the version

	Example:

		cat myFile.json | jsonToCsv '+"Results"["name", "org"]'



Module
======

The primary public module is json_to_csv.JsonToCsv

The constructor requires only the format string [formatStr] ( a string written in a simple specific meta-language used to define the pattern for extraction ).

You may, however, choose to define an alternate value to represent unreachable or defined-as-null fields [nullValue]


Module PyDoc
------------

You can access the pydoc here: http://htmlpreview.github.io/?https://github.com/kata198/jsonToCsv/blob/master/doc/index.html



Module Usage Example
--------------------

See: https://github.com/kata198/jsonToCsv/blob/master/example.py and https://github.com/kata198/jsonToCsv/blob/master/example_mutli.py.

For a basic example of using the module directly for extraction and reformatting into various formats (CSV, TSV, a text table)


Extracting Data
---------------

Once you've written your formatStr and created the JsonToCsv object, you're ready to start parsing!


**extractData**

extractData is the "core" method of JsonToCsv. It performs the actual work of taking the json and following the format string to create a series of lines.

The output of this method is a list of lists, the outer list is each line, and each line is a list where each element represents a field.

Some more complicated use-cases where "extractData" is required are:

* Creating alternate formats of output (like TSV or a text table, or plugging into a GUI)

* Analysis of the data, i.e. filtering or modifying

* Joining data from multiple JSON entries (see that section for more info)

* Whatever you need to do

You can pass the output of this function to the "dataToStr" method to convert it into a printable string.

**dataToStr**

dataToStr provides the means to convert data (from extractData) to a printable string.

The first argument is the list-of-lists that extractData provides

It then has the following optional arguments:

* separator - Defaults to comma, may use tab for TSV, or whatever you want

* lineSeparator - Defaults to CRLF (\\r\\n) which is the RFC4180 standard, but you may use something else (like \\n).

* quoteFields - This you can set to True or False to explicitly quote or not quote data per RFC4180 standards. The default is the string "smart", which means the data will be scanned to see if it needs quoting, and if so, it will quote the data. Otherwise, it will not. Generally you will want to keep this at the default.


**convertToCsv**

The most basic and direct method is the "convertToCsv" function. You can pass in a string (raw data) or a dict (already parsed e.g. by 'json' module ), and you'll be output the csv lines, ready to be passed to the "print" function. 

This is the same as calling extractData and passing it to dataToStr, except you can only use comma as a separator through this function.

This function takes the same "lineSeparator" and "quoteFields" arguments described in "dataToStr" above.


**findDuplicates**

This function can help you identify when multiple lines contain the same data in the same field. 

You pass in the data extracted by *extractData*, pick a zero-origin "fieldNum", which dictates which field to check on each line for duplicate values.

If the "flat" argument is False (default), the output is a map where the keys are all the field values which had duplicate entries.

If "flat" is True, the output is just a list of list-of field values. Basically, the data from extractData, but ONLY included if it has a duplicate in the chosen field.


**joinCsv**

joinCsv will take in two sets of list<list<str>> (i.e. returned frmo "extractData"), and two 0-origin numbers, joinFieldNum1 (what is the index of the "join field" in the first dataset) and joinFieldNum2.

So for example, you may have two sets of data, both describing people. "Social Security Number" could be the 4th field from zero on one of them, and the 0th on another dataset. So if you want to combine these two datasets, you can use this method to do so, bt joining those fields (i.e. any instances where there's a field match between the two joinFieldNum columns, that index is removed from the second dataset, sand the second dataset is appended to the first.

**multiJoinCsv**

Same as joinCsv, but joinCsv allows no duplicates within a dataset itself. So going with the data above, imagine if the same social security number had two people's names in one dataset.... well which one is rght? A computer can't determine that.

So this function will give a "best effort", in the above example, you'd get person X's dataset attached to whoemver had that social security number listed. So if you have a field duplicated twice in both csvData1 and csvData2, you'll end up with 4 lines total:


* A1 B1
* A2 B1
* A1 B2
* A2 B3

This matches very eagerly, but you may start to get some invalid data at this point.




FULL EXAMPLE:
--------------

	."Data"[ +"Instances"[ "hostname", /"attrs"["key"="role" "value"], /"attrs"["key"="created_at" "value", "who_set"], ."Performance"[ "cpus", "memory" ] ] ]


**Explanation:**


The given json object will first be descended by the "Data" key, where a map is expected.

In this map, "Instances" will be the "line item", i.e. we will iterate over each item in the "Instances" list to generate each line of the csv.

So, for each map in "Instances":

   * We print the "hostname" key as the first csv element

   * We descend into a list of maps under the key "attrs",
   
   * Search for where one of those maps has an entry "key" with the value "role", and we print the value of the "value" key of that map as the second csv element.

Then, we return to previous level.

We descend again into that list of maps under the key "attrs",

   * Search for where one of those maps has an entry "key" with the value "created_at",
     and we print the value of the "value" key of that map as the third csv element.

   * We then print value of the "who_set" key of that same map as the fourth csv element.

Then, we return to the previous level

We then descend into a map under the key 'Performance'

   * we print the value of the key "cpus" at this level as the fifth csv element.
   * we print the value of the key "memory" at this level as the sixth csv element.

Then, we return to the previous level

We return to the previous level

(we are done iterating at this point)

We return to the previous level

**Example with inline comments:**

The following is the meant to parse the following json: https://github.com/kata198/jsonToCsv/blob/master/example_multi.json


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


