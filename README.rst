jsonToCsv
=========

Converts json data to csv


Module
======

The primary public module is json_to_csv.**JsonToCsv**

The constructor requires only the format string [formatStr] ( a string written in a simple specific meta-language used to define the pattern for extraction ).

You may, however, choose to define an alternate value to represent unreachable or defined-as-null fields [nullValue]


Format String
=============

Because csv is a fixed-format field and json is free-format, a meta language had to be developed to describe the various movements to find and output values into a fixerd format. This section describes that format.

**Format str:**

	The format str is a series of operations and keys, plus one or more "line item"s.

**Keys:**

	
	Every key name listed in the format string is quoted with double-quotes.

	If the key is prefixed with an operation, it is used to REACH a value.

	If a key is NOT prefixed with an operation, it becomes a value printed.

	Unless you are using an op to change level, the quoted key should be followed
	 by a comma to separate.

	A key may be anywhere before, after, or inside a line item, and the keys will be output in the order they appear.

	Examples:

	   "hostname"   # Print key hostname at current level

	   ."hostname"[ # The . (map access) operator applied on the "hostname" key

	   "hostname", "cheese" # Two keys at this current level
	

**Line Item:**

	A "line item" is the key iterated-over to produce each line of the csv.

	A line item is given with the '+' sign before a key.

	You may have multiple line items (so iterate over multiple keys), and you will have

	  one line of output per each innermost line item found.

	You may not close a line item and then try to open another one.



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


Commas:

	Commas should be used to separate items on the same level, so after a quoted-key for printing,
	and after a close-bracket "]" if more items follow on that upper level.

Order:

	Keys are printed as found left-to-right in the format string.

	You can descend into levels, back up, print keys, then descend back into those levels as many
	  times as you like.


Nulls:

	 If a value in the json map is "null" or undefined, an empty string is given for the value.

	 If there is an error following the format string to a key (like a missing key, or bad type),

	 you can pass the '--debug' flag to print on stderr WHY it returned null, each time that it does.

Case sensitive:

	All keys are case sensitive.

Multi-Line:

	Because non-quoted whitespace is ignored, you can use newlines, spaces, and tabs to make long patterns more readable.



Extracting Data
---------------

Once you've written your formatStr and created the JsonToCsv object, you're ready to start parsing!

**convertToCsv**

The most basic and direct method is the "convertToCsv" function. You can pass in a string (raw data) or a dict (already parsed e.g. by 'json' module ), and you'll be output the csv lines, ready to be passed to the "print" function. 

If you set the optional parameter "asList" to True (default is False), instead of being returned a giant string, you'll get a list where each element represents a line.


**extractData**

Likely however, you don't just need to convert it directly to csv if you are working with the module (it is recommended if that is the case, i.e. if you have no extra processing  or analysis or whatever required, that you use the provided "jsonToCsv" function).

Some more complicated use-cases where "extractData" is required are:

* Creating alternate formats of output (like TSV or a text table, or plugging into a GUI)
* Analysis of the data, i.e. filtering or modifying
* Joining data from multiple JSON entries (see that section for more info)
* Whatever you need to do


*extractData* works the same way as *convertToCsv*, that is you can pass in a string of a json response, or a dict (the already converted object by json module).



**dataToStr**

For many of the use-cases where you need to post-process or post-filter the data or whatever, you will eventually want to convert it to a printable string.

This is a function that does just that; you pass in the list-of-lists *extractData* returns, and you get a complete string returned, ready-to-go for the print function.


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


TODO: write more.

TODO: finish


Module PyDoc
------------

You can access the pydoc here: http://htmlpreview.github.io/?https://github.com/kata198/jsonToCsv/blob/master/doc/index.html


Module Usage Example
--------------------

See: https://github.com/kata198/jsonToCsv/blob/master/example.py .

For a basic example of using the module directly for extraction and reformatting into various formats (CSV, TSV, a text table)


Tool
====

Usage: jsonToCsv [format str]
  Formats a json string ( delivered via stdin ) to csv, based on provided format str.



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

