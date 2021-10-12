'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

function Expression() {}

Expression.prototype = Object.create(Array.prototype);
objectAssign(Expression.prototype, {
  toString: function toString() {
    let strs = this.map(x => x.toString());
    return `( ${strs.join(' ')} )`;
  },
  constructor: Expression
});
module.exports = Expression;