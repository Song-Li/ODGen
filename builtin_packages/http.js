var request_builtin_object = function(){
  var OPGen_TAINTED_VAR_url = "" ;
  var source_hqbpillvul_url = OPGen_TAINTED_VAR_url;
  this.url = source_hqbpillvul_url;
  this.path = source_hqbpillvul_url;

  this.on = function(str, cb) {
    // on should be counted as input
    var data1 = source_hqbpillvul_url;
    var data2 = source_hqbpillvul_url;
    cb(data1, data2);
  }
}

var response_builtin_object = function() {
  this.setHeader = function(key, value) {
    sink_hqbpillvul_http_setHeader(value);
  }

  this.write = function(value, value) {
    sink_hqbpillvul_http_write(value, value);
  }

  this.end = function(value, value) {
    sink_hqbpillvul_http_write(value, value);
  }

  this.send = function(value) {
    sink_hqbpillvul_http_write(value);
  }
}

var server = function() {
  var req = new request_builtin_object();
  var res = new response_builtin_object();
  this.on = function(key, cb) {
    cb(req, res);
  }
}

function createServer(requestListener, cb) {
  var req = new request_builtin_object();
  var res = new response_builtin_object();
  requestListener(req, res);
  cb(req, res);
  return new server();
}

module.exports = {
  createServer,
  request_builtin_object,
  response_builtin_object
};
