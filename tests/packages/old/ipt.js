function foo(input, val) {
  var internal = {'a': 123};
  internal[input] = val;
  return internal.a
}

module.exports = {
  foo: foo
}
