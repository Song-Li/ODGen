function foo(key1, key2, value) {
  var target = {};
  var mid = target[key1];
  mid[key2] = value;
}
function input_value(val) {
  var mid = val + " ";
  return mid;
}

function pp(key1, key2, value) {
  mid = input_value(value);
  foo(key1, key2, mid);
}

module.exports = {pp: pp}
