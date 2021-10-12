var cp = require("child_process");

var foo = function(input) {
  this.src = input;

  this.vul = function(input) {
    var src = input + '/cmd';
    cp.exec(src);
  }
}

module.exports = {
  foo: foo
}
