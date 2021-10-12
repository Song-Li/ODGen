var cp = require("child_process");
class foo {
  constructor (input){
    this.src = input;
  }

  vul () {
    cp.exec(this.src);
  }
}

function expolit(input) {
  var f = new foo(input);
  f.vul();
}

module.exports = {
  foo: foo,
  expolit: expolit
}
