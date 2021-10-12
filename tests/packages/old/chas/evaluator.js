'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

const Duplex = require('stream').Duplex;

const BeaconError = require('./error');

const Logger = require('./logger');

const Env = require('./env');

const Expression = require('./expression');

const Token = require('./token');

const SpecialForms = ['if', 'cond', 'quote', 'set', 'lambda'];

function a(str) {
  return new Token.Atom(str);
}

function EvalError() {}

EvalError.prototype = Object.create(BeaconError.prototype);
objectAssign(EvalError.prototype, {
  constructor: EvalError
});

function Evaluator(options) {
  Duplex.call(this, { ...{
      readableObjectMode: true,
      writableObjectMode: true
    },
    ...options
  });
  this.results = [];
  this.env = Env.default();
  this.still_receiving = true;
  Logger.INFO(this.env);
}

Evaluator.prototype = Object.create(Duplex.prototype);
objectAssign(Evaluator.prototype, {
  _write: function _write(chunk, _encoding, callback) {
    try {
      let got_result = this.eval(chunk);
      Logger.INFO(got_result);
      this.results.push(got_result);
    } catch (err) {
      return callback(err);
    }

    return callback(null);
  },
  _destroy: function _destroy(err, callback) {
    this.still_receiving = false;
    callback(err);
  },
  _final: function _final(callback) {
    this.still_receiving = false;
    callback();
  },
  _read: function _read() {
    while (true) {
      if (0 == this.results.length) {
        if (!this.still_receiving) {
          this.push(null);
          return;
        }

        setImmediate(this._read.bind(this));
        return;
      }

      let got = this.push(this.results.shift());
      if (false == got) return;
    }
  },
  eval: function eval(expr) {
    let first = expr.shift();
    Logger.INFO(first);

    if (a('quote').eq(first)) {
      return expr;
    }

    if (a('if').eq(first)) return this.do_if(expr);
    if (a('cond').eq(first)) return this.do_cond(expr);
    if (a('set').eq(first)) return this.do_set(expr); // if (a('lambda') == first) return this.do_lambda(expr)

    let rest = expr.map(a => this.inner_eval(a));
    Logger.INFO(`eval ${first}(${rest})`);

    if (first instanceof Token.Atom) {
      let sym = first.atom;
      let got = this.env.get(sym);
      return got(rest);
    }

    throw new EvalError(`couldn't eval ${first} (typeof ${typeof first})`);
  },
  inner_eval: function inner_eval(arg) {
    if (arg instanceof Expression) return this.eval(arg);
    if (arg instanceof Token.Atom) return this.env[arg];
    if (arg instanceof Token.Base) return arg.castJS();
    return arg;
  },
  is_truthy: function is_truthy(thing) {
    if (thing instanceof Array) return 0 != thing.length;
    return true;
  },
  do_if: function do_if(expr) {
    let predicate = expr[0];
    let true_leg = expr[1];
    let false_leg = expr[2];
    let result = this.inner_eval(predicate);
    if (this.is_truthy(result)) return this.inner_eval(true_leg);
    if (false_leg) return this.inner_eval(false_leg);
    return [];
  },
  do_cond: function do_cond(expr) {
    if (0 == expr.length) return [];
    let predicate = expr.shift();
    let leg = expr.shift();
    let result = this.inner_eval(predicate);
    if (this.is_truthy(result)) return this.inner_eval(leg);
    return this.do_cond(expr);
  },
  do_set: function do_set(expr) {
    let name = expr[0];
    let value = expr[1];
    Logger.INFO(`set ${name} to ${value} ${typeof value}`);
    this.env[name] = value;
    return value;
  },
  constructor: Evaluator
});
module.exports = Evaluator;