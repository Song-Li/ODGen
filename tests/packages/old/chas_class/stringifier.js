'use strict'

const Transform = require('stream').Transform

const Logger = require('./logger')

class Stringifier extends Transform {
    constructor(options) {
        super({
            ...{writableObjectMode: true},
            ...options
        })
    }

    _transform(chunk, _encoding, callback) {
        Logger.INFO(chunk.toString())
        this.push(chunk.toString() + "\n")
        callback()
    }
}

module.exports = Stringifier
