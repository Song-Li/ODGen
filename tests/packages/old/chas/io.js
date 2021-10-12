function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

const EventEmitter = require("events");

function Io(i, o) {
  this.i = i;
  this.i.setEncoding('UTF-8');
  this.o = o;
}

objectAssign(Io.prototype, {
  destroy: function destroy() {
    this.i.destroy();

    if (this.o != this.i) {
      this.o.destroy();
    }
  }
});
objectAssign(Io, {
  fromStdio: function fromStdio() {
    return new Io(process.stdin, process.stdout);
  }
});
module.exports = Io;