var mid = require("mid.js");
var http = require("http");
http.createServer(function (req, res) {
  mid.foo(req.url);
})
