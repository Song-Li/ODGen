var cp = require("child_process");

function expolit(string, input, val){
  var inner = string + "123";
  var base = {"basekey": inner};
  var the_end = "Nothing";
  var mid = the_end + "mid";

  for (var key in base) {
    var nothing = key + base[key];
  }

  if (inner == "bad") {
    var nothing = base['basekey'] + "abc";
  } else {
    var link = inner + "123";
  }
  cp.exec(link);
  my_sink(link);
  cp.exec(mid);
}
module.exports = {
  expolit};
