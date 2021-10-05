function waterfall(funcs, cb) {
  funcs.forEach(function(func){func()});
  cb("error");
}

module.exports = {
  waterfall
};
