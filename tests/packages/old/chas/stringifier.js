'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

const Transform = require('stream').Transform;

const Logger = require('./logger');

function Stringifier(options) {
  Transform.call(this, { ...{
      writableObjectMode: true
    },
    ...options
  });
}

Stringifier.prototype = Object.create(Transform.prototype);
objectAssign(Stringifier.prototype, {
  _transform: function _transform(chunk, _encoding, callback) {
    Logger.INFO(chunk.toString());
    this.push(chunk.toString() + "\n");
    callback();
  },
  constructor: Stringifier
});
module.exports = Stringifier;