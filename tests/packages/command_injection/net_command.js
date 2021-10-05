var net = require('net');
var sqlite3 = require('better-sqlite3');

var server = net.createServer(function(connection) { 
  var db = new sqlite3();
  var insert = db.prepare('INSERT INTO cats (name, age) VALUES (@name, @age)');

  connection.on('data', function(msg){
    insert.run(msg + ':123');
    db.table('fake', msg + ':234');
  });

  connection.on('end', function() {
    console.log('client disconnected');
  });

  connection.write('Hello World!\r\n');
  connection.pipe(connection);
});
