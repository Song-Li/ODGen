'use strict'

const Token = require('./token')

function a(str) { return str }

function c(obj) {
    if ("function" == typeof obj.castJS) return obj.castJS()
    if ([] == obj) return false

    return obj
}
function r(obj) {
    if ("string" == typeof obj) return new Token.String(obj)
    if ("number" == typeof obj) return new Token.Number(obj)

    return obj
}

function b(obj) {
    if (false == obj) return []
    return obj
}

class Env extends Map {
    static default() {
        var e = new Env()
        e.set(a('+'), rest => { return rest.reduce((a, n) => r(c(a) + c(n))) })
        e.set(a('-'), rest => { return rest.reduce((a, n) => r(c(a) - c(n))) })
        e.set(a('*'), rest => { return rest.reduce((a, n) => r(c(a) * c(n))) })
        e.set(a('/'), rest => { return rest.reduce((a, n) => r(c(a) / c(n))) })

        e.set(a('<'), rest => { return b(c(rest[0]) < c(rest[1])) })
        e.set(a('<='), rest => { return b(c(rest[0]) <= c(rest[1])) })
        e.set(a('>'), rest => { return b(c(rest[0]) > c(rest[1])) })
        e.set(a('>='), rest => { return b(c(rest[0]) >= c(rest[1])) })
        e.set(a('='), rest => { return b(c(rest[0]) == c(rest[1])) })
        e.set(a('!='), rest => { return b(c(rest[0]) != c(rest[1])) })

        e.set(a('car'), rest => { return rest[0] })
        e.set(a('cdr'), rest => { return rest.slice(1) })

        e.set(a('inspect'), rest => {
            let inner = rest.map((e) => e.toString()).join(', ')
            return new Token.String(inner)
        })

        e.set(a('puts'), rest => {
            console.log(rest.toString())
            return rest
        })

        return e
    }
}

    module.exports = Env
