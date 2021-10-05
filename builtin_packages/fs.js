function read(a, b, c, d, e, f) {
  var ret = sink_hqbpillvul_fs_read(a,b,c,d,e);
  b();
  c();
  d();
  e();
  f();
  return ret;
}

function readFile(pathname, options, cb) {
  // just build a link from pathname to cb
  // mark the path used read
  // we need to + 'x' to generate a new obj here
  var ret = sink_hqbpillvul_fs_read(pathname);
  cb(ret == '123', ret);
  // incase options is cb
  options(ret == '123', ret);
  return ret;
}

module.exports = {
  read: read,
  readdir: readFile,
  readdirSync: readFile,
  readFile: readFile,
  readFileSync: readFile,
  readlink: read,
  readlinkSync: read,
  readSync: read,
  createReadStream: read
}
