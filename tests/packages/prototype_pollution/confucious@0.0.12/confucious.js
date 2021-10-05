'use strict';

module.exports = function () {

	var fs = require('fs');
	var argv = require('yargs').argv;
	var extend = require('extend');

	var globalValues = {};
	var baseValues = {};
	var valuesStack = [];

	valuesStack.push(globalValues);
	valuesStack.push(baseValues);

	//
	// Debug only function to get the current state of the value stack.
	// NOTE: This deep copies the data so that it cannot be modified externally this
	// ensures the managed configuration is immutable.
	//
	this.getValueStackCopy = function () {
		return extend(true, [], valuesStack);
	};

	//
	// Set a value by key at the top level of the key/value staci.
	//
	this.set = function (key, value) {
		var keyParts = key.split(':');
		var hash = valuesStack[valuesStack.length-1];

		for (var i = 0; i < keyParts.length-1; ++i) {
			var subKey = keyParts[i];
			hash = hash[subKey];
			if (typeof(hash) === 'undefined') {
				hash = {};
				hash[subKey] = hash;
			}
		}

		var lastKeyPartIndex = keyParts.length-1;
		var lastSubKey = keyParts[lastKeyPartIndex];

		if (typeof(value) === 'object') {
			hash[lastSubKey] = extend(true, {}, value);
		}
		else {
			hash[lastSubKey] = value;
		}
	};

	//
	// Clear a key from the top level of the key/value stack.
	//
	this.clear = function (key) {
		var keyParts = key.split(':');
		var hash = valuesStack[valuesStack.length-1];

		for (var i = 0; i < keyParts.length-1; ++i) {
			var subKey = keyParts[i];
			hash = hash[subKey];
			if (typeof(hash) === 'undefined') {
				return;
			}
		}

		var lastKeyPartIndex = keyParts.length-1;
		var lastSubKey = keyParts[lastKeyPartIndex];
		delete hash[lastSubKey];
	};

	//
	// Set a global key/value.
	//
	this.setGlobal = function (key, value) {
		globalValues[key] = value;
	};

	//
	// Clear a global key/value.
	//
	this.clearGlobal = function (key) {
		delete globalValues[key];
	};

	//
	// Get a value from the specified object. 
	// Returns undefined if not found.
	//
	var getValue = function (key, hash) {

		var value = hash[key];
		if (typeof(value) !== 'undefined') {
			return value;
		}

		return undefined;
	};

	//
	// Get a nested value from the specified object.
	// Returns undefined if not found.
	//
	var getNestedValue = function (keyParts, hash) {

		for (var i = 0; i < keyParts.length-1; ++i) {
			hash = getValue(keyParts[i], hash);
			if (typeof(hash) === 'undefined') {
				return undefined;
			}
		}

		var lastKeyPartIndex = keyParts.length-1;
		return getValue(keyParts[lastKeyPartIndex], hash)
	};

	//
	// Get a value by key.
	// Key can reference a nested value.
	// Searches all levels in the key/value stack.
	// Returns undefined if the key does not exist anywhere.
	//
	this.get = function (key) {

		var keyParts = key.split(':');

		for (var i = valuesStack.length-1; i >= 0; --i) {
			var value = getNestedValue(keyParts, valuesStack[i]);
			if (typeof(value) !== 'undefined') {
				return value;
			}
		}

		return undefined;
	};

	//
	// Push a set of key/values on the key/value stack.
	//
	this.push = function (values) {
		valuesStack.push(extend(true, {}, values));
	};

	//
	// Pop a set of values from the stack.
	//
	this.pop = function () {
		if (valuesStack.length > 2) {
			valuesStack.pop();
		}
		else {
			// Can't push the base levels of the stack.
		}		
	};

	//
	// Load a json file and push it on the key/value stack.
	//
	this.pushJsonFile = function (filePath) {
		this.push(JSON.parse(fs.readFileSync(filePath, 'utf8')));
	};

	//
	// Push arguments onto the key/value stack.
	//
	this.pushArgv = function () {
		this.push(argv);
	};

	//
	// Push environment variables onto the key/value stack.
	//
	this.pushEnv = function () {
		this.push(process.env);
	};

	//
	// Get the current configuration as a JavaScript object.
	//
	this.toObject = function () {
		var base = {};

		valuesStack.forEach(function (value) {
			base = extend(base, value);
		});

		return base;
	};
};