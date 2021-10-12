'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

function BeaconError() {}

BeaconError.prototype = Object.create(Error.prototype);
objectAssign(BeaconError.prototype, {
  constructor: BeaconError
});
module.exports = BeaconError;