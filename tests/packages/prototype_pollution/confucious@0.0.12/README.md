# confucious

A simple, stack-based, key/value configuration manager. 

Kind of like nconf, but easier to use, predicable and more flexible.

## Installation

	npm install --save confucious

## Usage

### Setup

	var conf = require('confucious');

### Setting a key/value

	conf.set("key", "some-value");

### Getting a key/value

	var value = conf.get("key");

### Stack based storage

A hash of keys/values can be pushed on top of the 'key/value stack'. 

	conf.push({
		"key": "some-value",
	});

When you get a value that is defined higher in the stack, that value overrides underlying values.

	var value = conf.get("key"); // Search stack for a value for "key"

When you set a key/value, the value is modified at the top level of the stack:

	conf.set("key", "some-other-value"); // Set values on top of the stack.

The last key/values hash that was pushed can be popped.

	conf.pop(); // Revert to stack level underneath.

### Global key/values

When you call `set` and `clear` these functions operate (setting or clearing a key/value) at the top level of the stack. This means whatever level you pushed on the stack last will be modified. If you pop that level from the stack the modifications will be lost.

To persist values you may want to set and clear global values:

	conf.setGlobal('some-key', 'some-value');

	conf.clearGlobal('some-key');

When you set a global it sets the value at the bottom level of the stack. So the value persists regardless of what other stack levels you push or pop.

Note that global key/values are same as any other key/value with the exception that they are at the bottom of the stack. Therefore they can be overridden by key/values higher in the stack.  

### Nested key/values

Similar to nconf, Confucious supports the colon key (:) as a separator for getting, setting and clearing nested key/values.

	conf.push({
		"some-key": {
			"some-nested-key": "some-value",
		}
	});

	var value = conf.get("some-key:some-nested-key"); // == "some-value"

	conf.set("some-key:some-nested-key", "some-other-value");

	conf.clear("some-key:some-nested-key");	

### Current configuration

Dump the entire current configuration to JavaScript object (good for debugging):

	var curConfiguration = conf.toObject();
	console.log(curConfiguration);

### Load a file

	conf.pushJsonFile("path/to/file.json");

### Load environment variables

	conf.pushEnv();

### Load command line arguments

	conf.pushArgv();

	


