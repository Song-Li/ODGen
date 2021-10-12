const EventEmitter = require("events")

class Io {
    constructor(i, o) {
        this.i = i
        this.i.setEncoding('UTF-8')

        this.o = o
    }

    static fromStdio() {
        return new Io(process.stdin, process.stdout)
    }

    destroy() {
        this.i.destroy()
        if (this.o != this.i) {
            this.o.destroy()
        }
    }
}

module.exports = Io
