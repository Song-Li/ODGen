var cp = require("child_process");
function end(input) {
  var endvar = input + "end";
  cp.exec(endvar);
}

module.exports = {
  end: end
}
