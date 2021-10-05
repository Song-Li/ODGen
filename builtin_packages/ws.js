var request_builtin_object = function(){
  var source_hqbpillvul_url = '';
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

function ws(requestListener) {
  var req = new request_builtin_object();
  var res = new response_builtin_object();
  requestListener(req, res);

  this.Server = function(server_obj) {
    this.http_server = server_obj;
  }
  this.on = function(service_key, cb) {
    if (service_key == 'open') {
      cb(req.url);
    } else if (service_key == 'message') {
      cb(req.url);
    } else if (service_key == 'close') {
      cb(req.url);
    } else if (service_key == 'connection') {
      cb(req.url);
    } else if (service_key == 'upgrade') {
      cb(req, res, req.url);
    }
  }
  this.send = function(msg) {
    sink_hqbpillvul_http_write(msg);
  }
  this.handleUpgrade = function(request, socket, head, cb) {
    this.req = request;
    this.socket = socket;
    cb(this);
  }
}


module.exports = ws
