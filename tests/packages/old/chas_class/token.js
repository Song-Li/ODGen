'use strict'

const BeaconError = require('./error')

class CastError extends BeaconError {
    constructor(from, to_name) {
        super(`failed to cast ${from} to a ${to_name}`)
    }
}

class Base {
    castJS() {
        throw CastError(this, 'JS thing')
    }
}

class Atom extends Base {
    constructor(atom_str) {
        super()
        this.atom = atom_str
    }

    toString() {
        return `Atom(${this.atom})`
    }

    eq(other) {
        if (! other instanceof Atom) return false;
        if (this.atom != other.atom) return false;

        return true
    }
}

class OpenList extends Base {
    toString() {
        return '('
    }
}

class CloseList extends Base {
    toString() {
        return ')'
    }
}

class Number extends Base {
    constructor(num) {
        super()
        this.num = num
    }

    toString() {
        return this.num.toString()
    }

    castJS() {
        return this.num
    }
}

class String extends Base {
    constructor(str) {
        super()
        this.str = str
    }

    toString() {
        return `"${this.str}"`
    }

    castJS() {
        return this.str
    }
}

module.exports = {
    Atom: Atom,
    Base: Base,
    Number: Number,
    String: String,

    OpenList: OpenList,
    CloseList: CloseList
}
