function Insert(sinks) {
  // the return obj of sqlite
  this.sinks = sinks;
  this.run = function() {
    for (i in arguments) {
      sink_hqbpillvul_db(this.sinks, arguments[i]);
    }
  }
}

function Transaction(sinks) {
  Transaction.cb(sinks);
}
Transaction.deferred = function(sinks){
  Transaction.cb(sinks);
}
Transaction.immediate = function(sinks){
  Transaction.cb(sinks);
}
Transaction.exclusive = function(sinks){
  Transaction.cb(sinks);
}

function Sqlite3(db_name, options) {
  this.prepare = function(command) {
    this.command = command;
    var ins_obj = new Insert(this.command);
    return ins_obj;
  }
  this.transaction = function(cb) {
    Transaction.cb = cb;
    return Transaction;
  }
  this.pragma = function(args) {
    sink_hqbpillvul_db(args);
  }
  this.backup = function(args) {
    sink_hqbpillvul_db(args);
  }
  this.table = function() {
    for (var i in arguments) {
      sink_hqbpillvul_db(arguments[i]);
    }
  }
  this.exec = function(command) {
    sink_hqbpillvul_db(command);
  }
}


module.exports = Sqlite3;
