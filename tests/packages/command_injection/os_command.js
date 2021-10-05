var cp = require("child_process");

function expolit(string, input, val){
  var inner = string + "123";
  var base = {"basekey": inner};
  var mid = "123";
  var end = mid + "";

  for (var key in base) {
    var nothing = key + base[key];
  }

  if (inner == "bad") {
    var nothing = base['basekey'] + "abc";
  } else {
    var link = inner + "123";
  }
  cp.exec(link);
  cp.exec(end);
}
module.exports = {
  expolit};
