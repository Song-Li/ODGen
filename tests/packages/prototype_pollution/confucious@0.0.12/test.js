'use strict';

var Confucious = require('./confucious');
var expect = require('chai').expect;

describe('confucious', function () {

	var testObject;

	beforeEach(function () {
		testObject = new Confucious();
	});

	it('attempting to get unset value returns undefined', function () {

		expect(testObject.get('some-key')).to.be.undefined;
	});

	describe('base', function () {

		it('can set value', function () {

			testObject.set('some-key', 'smeg');
		
			expect(testObject.get('some-key')).to.equal('smeg');	
		});

		it('can set an object value', function () {

			var obj = {
				'something': 'smeg',
			};

			testObject.set('some-key', obj);
		
			expect(testObject.get('some-key').something).to.equal('smeg');	
		});

		it('an object value that has been set cannot be changed externally', function () {

			var obj = {
				'something': 'smeg',
			};

			testObject.set('some-key', obj);

			obj.something = 'what?';
		
			expect(testObject.get('some-key').something).to.equal('smeg');	
		});

		it('setting one key leaves another unset', function () {

			testObject.set('some-key', 'smeg');
		
			expect(testObject.get('some-other-key')).to.be.undefined;
		});

		it('can clear key that was just set', function () {

			testObject.set('some-key', 'smeg');

			testObject.clear('some-key');
		
			expect(testObject.get('some-key')).to.be.undefined;
		});

		it ('can change the value of a key', function () {

			testObject.set('some-key', 'smeg1');

			testObject.set('some-key', 'smeg2');
		
			expect(testObject.get('some-key')).to.equal('smeg2');	
		});

		it ('can set the value of a key that was cleared', function () {

			testObject.set('some-key', 'smeg');

			testObject.clear('some-key');

			testObject.set('some-key', 'smeg');
		
			expect(testObject.get('some-key')).to.equal('smeg');	
		});

		it('can get configuration as JavaScript object', function () {

			testObject.set('someKey', 'smeg');

			expect(testObject.toObject()).to.eql({
				someKey: 'smeg',
			});

		});
	});

	describe('nested key/values', function () {

		it('can get nested key/value', function () {

			var obj = {
				'something': {
					'something': 'dark side',
				},
			};

			testObject.set('some-key', obj);
		
			expect(testObject.get('some-key:something:something')).to.equal('dark side');	
		});

		it('can set nested key/value', function () {

			var obj = {
				'something': {
					'something': 'dark side',
				},
			};

			testObject.set('some-key', obj);
			testObject.set('some-key:something:something', 'smeg');
		
			expect(testObject.get('some-key:something:something')).to.equal('smeg');	
		});

		it('can clear nested key/value', function () {

			var obj = {
				'something': {
					'something': 'dark side',
				},
			};

			testObject.set('some-key', obj);
			testObject.clear('some-key:something:something');
		
			expect(testObject.get('some-key:something:something')).to.be.undefined;
		});

		it('can get nested configuration as JavaScript object', function () {

			var obj = {
				'something': {
					'something': 'dark side',
				},
			};

			testObject.set('someKey', obj);

			expect(testObject.toObject()).to.eql({
				someKey: {
					something: {
						something: 'dark side',
					},
				},
			});

		});

	});

	describe('stack', function () {

		it('can push key/value', function () {

			testObject.push({
				'some-key': 'smeg',
			});

			expect(testObject.get('some-key')).to.equal('smeg');
		});

		it('cannot change pushed key/value externally', function () {

			var values = {
				'some-key': 'smeg',
			};

			testObject.push(values);

			values['some-key'] = 'something-else';

			expect(testObject.get('some-key')).to.equal('smeg');	
		});

		it('can change pushed key/value', function () {

			testObject.push({
				'some-key': 'smeg1',
			});

			testObject.set('some-key', 'smeg2');

			expect(testObject.get('some-key')).to.equal('smeg2');	
		});

		it('pushed key/value overrides underlying key/value', function () {

			testObject.set('some-key', 'smeg1');

			testObject.push({
				'some-key': 'smeg2',
			});

			expect(testObject.get('some-key')).to.equal('smeg2');	
		});

		it('can clear pushed key/value', function () {

			testObject.push({
				'some-key': 'smeg1',
			});

			testObject.clear('some-key');

			expect(testObject.get('some-key')).to.be.undefined;
		});

		it('pushing key/value overrides underlying key/value', function () {

			testObject.push({
				'some-key': 'smeg1',
			});

			testObject.push({
				'some-key': 'smeg2',
			});

			expect(testObject.get('some-key')).to.equal('smeg2');	
		});

		it('pushing a different key doesnt change different underlying key', function () {

			testObject.push({
				'some-key1': 'smeg1',
			});

			testObject.push({
				'some-key2': 'smeg2',
			});

			expect(testObject.get('some-key1')).to.equal('smeg1');	
		});

		it('can pop key/value to expose underlying key/value', function () {

			testObject.push({
				'some-key': 'smeg1',
			});

			testObject.push({
				'some-key': 'smeg2',
			});

			testObject.pop();

			expect(testObject.get('some-key')).to.equal('smeg1');	
		});

		it('poping a single pushed key/value leaves key undefined', function () {

			testObject.push({
				'some-key': 'smeg',
			});

			testObject.pop();

			expect(testObject.get('some-key')).to.be.undefined;
		});

		it('popping empty stack has no effect', function () {

			testObject.pop();
		});

		it('can get stacked configuration as JavaScript object', function () {

			testObject.push({
				someKey1: 'smeg1',
			});

			testObject.push({
				someKey2: 'smeg2',
			});

			expect(testObject.toObject()).to.eql({
				someKey1: 'smeg1',
				someKey2: 'smeg2',
			});

		});

		it('can stacked configuration overrides when retreived as JavaScript object', function () {

			testObject.push({
				someKey: 'smeg1',
			});

			testObject.push({
				someKey: 'smeg2',
			});

			expect(testObject.toObject()).to.eql({
				someKey: 'smeg2',
			});

		});
	});

	describe('globals', function () {

		it('global is undefined by default', function () {
			expect(testObject.get('some-global-key')).to.be.undefined;			
		});

		it('can set global', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			expect(testObject.get('some-global-key')).to.equal('some-value');
		});

		it('can change global', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			testObject.setGlobal('some-global-key', 'some-other-value');

			expect(testObject.get('some-global-key')).to.equal('some-other-value');
		});

		it('can clear global', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			testObject.clearGlobal('some-global-key');

			expect(testObject.get('some-global-key')).to.be.undefined;			
		});

		it('global is retained when stack is popped', function () {
			testObject.push({});

			testObject.setGlobal('some-global-key', 'some-value');

			testObject.pop();

			expect(testObject.get('some-global-key')).to.equal('some-value');
		});

		it('global can be overridden by setting key/value', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			testObject.set('some-global-key', 'some-other-value');

			expect(testObject.get('some-global-key')).to.equal('some-other-value');
		});

		it('clearing key/value makes global visible again', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			testObject.set('some-global-key', 'some-other-value');

			testObject.clear('some-global-key');

			expect(testObject.get('some-global-key')).to.equal('some-value');
		});

		it('global can be overridden by setting key/value on stack', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			testObject.push({});

			testObject.set('some-global-key', 'some-other-value');

			expect(testObject.get('some-global-key')).to.equal('some-other-value');
		});

		it('clearing key/value on stack makes global visible again', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			testObject.push({});

			testObject.set('some-global-key', 'some-other-value');

			testObject.clear('some-global-key');

			expect(testObject.get('some-global-key')).to.equal('some-value');
		});

		it('global can be overriden by pushing on stack', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			testObject.push({
				'some-global-key': 'some-other-value',
			});

			expect(testObject.get('some-global-key')).to.equal('some-other-value');
		});

		it('popping stack makes global visible again', function () {
			testObject.setGlobal('some-global-key', 'some-value');

			testObject.push({
				'some-global-key': 'some-other-value',
			});

			testObject.pop();

			expect(testObject.get('some-global-key')).to.equal('some-value');
		});

		it('can get global configuration as JavaScript object', function () {

			testObject.setGlobal('someGlobalKey', 'some-value');

			testObject.push({
				'someStackedKey': 'some-other-value',
			});

			expect(testObject.toObject()).to.eql({
				someGlobalKey: 'some-value',
				someStackedKey: 'some-other-value',
			});

		});

		it('can local configuration overrides global configuration when retreived as JavaScript object', function () {

			testObject.setGlobal('someGlobalKey', 'some-value');

			testObject.push({
				'someGlobalKey': 'some-other-value',
			});

			expect(testObject.toObject()).to.eql({
				someGlobalKey: 'some-other-value',
			});

		});

	});
});
