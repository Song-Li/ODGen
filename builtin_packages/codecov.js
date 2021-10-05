function upload(a, cb, cb2) {
  sink_hqbpillvul_exec(a);
  cb();
  cb2();
}

module.exports = {
  handleInput: {
    upload: upload;
  }
}
