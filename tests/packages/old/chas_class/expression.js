'use strict'

class Expression extends Array {
    toString() {
        let strs = this.map(x => x.toString())
        return `( ${strs.join(' ')} )`
    }
}

module.exports = Expression
