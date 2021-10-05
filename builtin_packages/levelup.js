function Levelup(input_path) {
  this.put = function(key, val) {
    var db_key = key;
    var db_val = val;
    sink_hqbpillvul_db(key, val);
  }
}

function levelup(input_path) {
  return new Levelup(input_path);
}

module.exports = levelup;
