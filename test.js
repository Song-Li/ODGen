var cp = require("child_process");
function foo(source1, source2) {
  function Func () {};
  Func.prototype.x="ab";
  myFunc = new Func;
  if (source1)
    myFunc[source2] = myFunc.x + source1; // internal property tampering
  cp.exec(myFunc.x); // taint
}
module.exports = {foo: foo}
