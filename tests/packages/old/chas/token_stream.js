'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

const util = require('util');

const Duplex = require("stream").Duplex;

const BeaconError = require("./error");

const Logger = require("./logger");

const Token = require("./token");

const NumberParser = /\d+(\.\d*)?[\s)(]/u;
const StringParser = /"((\\"|[^"])*)"[\s)(]/u;
const SymbolParser = /([a-zA-Z_+\-/*><=!][a-zA-Z0-9_+\-/*><=!]*)[\s)(]/u;
const OpenParser = /\(/u;
const CloseParser = /\)/u;
const QuoteUnescaper = /\\"/g;

function ScanError() {}

ScanError.prototype = Object.create(BeaconError.prototype);
objectAssign(ScanError.prototype, {
  constructor: ScanError
});

function TokenStream(options) {
  Duplex.call(this, { ...{
      readableObjectMode: true
    },
    ...options
  });
  this.tokens = [];
  this.max_held_tokens = 16;
  this.prev_chunk = "";
  this.still_receiving = true;
}

TokenStream.prototype = Object.create(Duplex.prototype);
objectAssign(TokenStream.prototype, {
  toString: function toString() {
    return `TokenStream[${this.tokens}]`;
  },
  isFull: function isFull() {
    return this.tokens.length === this.max_held_tokens;
  },
  _write: function _write(chunk, encoding, callback) {
    if ('buffer' == encoding) {
      chunk = chunk.toString();
    } else if ('UTF-8' != encoding) {
      let err = new ScanError(`unknown character encoding ${encoding}`);
      return callback(err);
    }

    try {
      this.consumeChunk(chunk);
      Logger.INFO(`consumed chunks ${this.tokens}`);
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
      if (0 == this.tokens.length) {
        if (!this.still_receiving) {
          this.push(null);
          return;
        }

        setImmediate(this._read.bind(this));
        return;
      }

      let cur_tok = this.tokens.shift();
      let got = this.push(cur_tok);
      if (false == got) return;
    }
  },
  consumeChunk: function consumeChunk(new_chunk) {
    let chunk = this.prev_chunk + new_chunk;
    let string_pos = chunk.search(StringParser);
    let number_pos = chunk.search(NumberParser);
    let symbol_pos = chunk.search(SymbolParser);
    let open_pos = chunk.search(OpenParser);
    let close_pos = chunk.search(CloseParser);
    let beyond_pos = chunk.length + 1;
    if (string_pos < 0) string_pos = beyond_pos;
    if (number_pos < 0) number_pos = beyond_pos;
    if (symbol_pos < 0) symbol_pos = beyond_pos;
    if (open_pos < 0) open_pos = beyond_pos;
    if (close_pos < 0) close_pos = beyond_pos;
    let min_pos = beyond_pos;
    if (string_pos < min_pos) min_pos = string_pos;
    if (number_pos < min_pos) min_pos = number_pos;
    if (symbol_pos < min_pos) min_pos = symbol_pos;
    if (open_pos < min_pos) min_pos = open_pos;
    if (close_pos < min_pos) min_pos = close_pos;

    if (min_pos == beyond_pos) {
      // nothing matched, done
      this.prev_chunk = new_chunk; // hold on for next time

      return undefined;
    }

    this.prev_chunk = "";
    if (min_pos == string_pos) return this.consumeString(chunk);
    if (min_pos == number_pos) return this.consumeNumber(chunk);
    if (min_pos == symbol_pos) return this.consumeSymbol(chunk);
    if (min_pos == open_pos) return this.consumeOpen(chunk);
    if (min_pos == close_pos) return this.consumeClose(chunk);
    throw ScanError(`couldn't figure out how to consume ${chunk}`);
  },
  consumeString: function consumeString(chunk) {
    let md = chunk.match(StringParser);

    if (undefined == md.index) {
      throw ScanError(`tried to consumeString but failed ${chunk}`);
    }

    let unescaped_contents = md[1].replace(QuoteUnescaper, '"');
    this.tokens.push(new Token.String(unescaped_contents));
    let remain = chunk.substr(md.index + md[0].length - 1);
    return this.consumeChunk(remain);
  },
  consumeNumber: function consumeNumber(chunk) {
    let md = chunk.match(NumberParser);

    if (undefined == md.index) {
      throw new ScanError(`tried to consumeNumber but failed ${chunk}`);
    }

    var val;

    if (undefined != md[1]) {
      val = parseFloat(md[0]);
    } else {
      val = parseInt(md[0]);
    }

    this.tokens.push(new Token.Number(val));
    let remain = chunk.substr(md.index + md[0].length - 1);
    return this.consumeChunk(remain);
  },
  consumeSymbol: function consumeSymbol(chunk) {
    let md = chunk.match(SymbolParser);

    if (undefined == md.index) {
      throw new ScanError(`tried to consumeSymbol but failed ${chunk}`);
    }

    let contents = md[1];
    this.tokens.push(new Token.Atom(contents));
    let remain = chunk.substr(md.index + md[1].length);
    return this.consumeChunk(remain);
  },
  consumeOpen: function consumeOpen(chunk) {
    let md = chunk.match(OpenParser);

    if (undefined == md.index) {
      throw new ScanError(`tried to consumeOpen but failed ${chunk}`);
    }

    this.tokens.push(new Token.OpenList());
    let remain = chunk.substr(md.index + 1);
    return this.consumeChunk(remain);
  },
  consumeClose: function consumeClose(chunk) {
    let md = chunk.match(CloseParser);

    if (undefined == md.index) {
      throw new ScanError(`tried to consumeClose but failed ${chunk}`);
    }

    this.tokens.push(new Token.CloseList());
    let remain = chunk.substr(md.index + 1);
    return this.consumeChunk(remain);
  },
  constructor: TokenStream
});
util.inherits(TokenStream, Duplex);
module.exports = TokenStream;