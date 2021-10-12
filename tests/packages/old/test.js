var cp = require("child_process");
function ipt(str, input, val) {
  var root = {};
  var ary = [];
  ary.join(" ");
  //str[input] = val;
  res = str.toString();
}
function expolit(string, input, val){
  var inner = string + 123;
  var base = {"basekey": inner};

  for (var key in base) {
    var nothing = key + base[key];
    eval(base[key]);
  }

  if (inner == "bad") {
    var nothing = base['basekey'] + "abc";
    eval(base['basekey']);
  } else {
    var link = inner + "123";
    eval(inner);
  }
  cp.exec(inner);

  try {
    var inner = 123;
  } catch (error) {
    console.log(error);
  }
}
module.exports = {
  expolit, ipt};
