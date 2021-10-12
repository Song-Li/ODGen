'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

const BeaconError = require('./error');

function CastError(from, to_name) {
  BeaconError.call(this, `failed to cast ${from} to a ${to_name}`);
}

CastError.prototype = Object.create(BeaconError.prototype);
objectAssign(CastError.prototype, {
  constructor: CastError
});

function Base() {}

objectAssign(Base.prototype, {
  castJS: function castJS() {
    throw CastError(this, 'JS thing');
  }
});

function Atom(atom_str) {
  Base.call(this);
  this.atom = atom_str;
}

Atom.prototype = Object.create(Base.prototype);
objectAssign(Atom.prototype, {
  toString: function toString() {
    return `Atom(${this.atom})`;
  },
  eq: function eq(other) {
    if (!other instanceof Atom) return false;
    if (this.atom != other.atom) return false;
    return true;
  },
  constructor: Atom
});

function OpenList() {}

OpenList.prototype = Object.create(Base.prototype);
objectAssign(OpenList.prototype, {
  toString: function toString() {
    return '(';
  },
  constructor: OpenList
});

function CloseList() {}

CloseList.prototype = Object.create(Base.prototype);
objectAssign(CloseList.prototype, {
  toString: function toString() {
    return ')';
  },
  constructor: CloseList
});

function Number(num) {
  Base.call(this);
  this.num = num;
}

Number.prototype = Object.create(Base.prototype);
objectAssign(Number.prototype, {
  toString: function toString() {
    return this.num.toString();
  },
  castJS: function castJS() {
    return this.num;
  },
  constructor: Number
});

function String(str) {
  Base.call(this);
  this.str = str;
}

String.prototype = Object.create(Base.prototype);
objectAssign(String.prototype, {
  toString: function toString() {
    return `"${this.str}"`;
  },
  castJS: function castJS() {
    return this.str;
  },
  constructor: String
});
module.exports = {
  Atom: Atom,
  Base: Base,
  Number: Number,
  String: String,
  OpenList: OpenList,
  CloseList: CloseList
};