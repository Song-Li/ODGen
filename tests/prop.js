var cp = require("child_process");
function prop(input) {
  var inner_tainted = input.tainted + " ";
  var inner_obj = input + " ";
  inner_tainted_obj = inner_obj.tainted;
  cp.exec(inner_tainted);
  cp.exec(inner_tainted_obj);
}

module.exports = {
  prop: prop
}
