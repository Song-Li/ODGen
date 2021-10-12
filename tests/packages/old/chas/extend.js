'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

var hasOwnProperty = Object.prototype.hasOwnProperty;

function extend_immutable() {
  var target = {};

  for (var i = 0; i < arguments.length; i++) {
    var source = arguments[i];

    for (var key in source) {
      if (hasOwnProperty.call(source, key)) {
        target[key] = source[key];
      }
    }
  }

  return target;
}

function extend_mutable(target) {
  for (var i = 1; i < arguments.length; i++) {
    var source = arguments[i];

    for (var key in source) {
      if (hasOwnProperty.call(source, key)) {
        target[key] = source[key];
      }
    }
  }

  return target;
}

module.exports = {
  immutable: extend_immutable,
  mutable: extend_mutable
};