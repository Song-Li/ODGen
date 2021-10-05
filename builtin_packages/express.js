var request_builtin_object = function(){
  var OPGen_TAINTED_VAR_url = "" ;
  var source_hqbpillvul_url = OPGen_TAINTED_VAR_url;
  var req_body = {
    'user': {
      'name':source_hqbpillvul_url
    }
  }
  this.url = source_hqbpillvul_url;
  this.path = source_hqbpillvul_url;
  this.body = req_body;
  this.user = source_hqbpillvul_url;
  this.params = [source_hqbpillvul_url, source_hqbpillvul_url, 
    source_hqbpillvul_url, source_hqbpillvul_url];

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
    return null;
  }

  this.render = function(loc, value) {
    sink_hqbpillvul_http_write(loc, value);
  }

  this.write = function(value) {
    sink_hqbpillvul_http_write(value);
  }

  this.end = function(value) {
    sink_hqbpillvul_http_write(value);
    return null;
  }

  this.send = function(value) {
    sink_hqbpillvul_http_write(value);
    return null;
  }

  this.sendFile = function(loc) {
    sink_hqbpillvul_http_sendFile(loc);
  }
}

get_new_express = function() {return new express()};

function express(requestListener) {
  var req = new request_builtin_object();
  var res = new response_builtin_object();
  requestListener(req, res);

  this.use = function(file_path, cb) {
    file_path(req, res);
    cb(req, res);
  }

  this.get = function(file_path, cb) {
    cb(req, res);
  }

  this.post= function(file_path, url, cb) {
    url(req, res);
    cb(req, res);
  }

  this.all = function(file_path, cb) {
    cb(req, res);
  }

  /*
  this.Router = function() {
    return this;
  }
  */
}

get_new_express.Router = function() {
  return get_new_express();
}


module.exports = get_new_express;
