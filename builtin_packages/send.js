var fs = require("fs");
function send(res, indexpath) {
  var file_res = fs.read(indexpath);
  res.send(file_res);
}

module.exports = send;
