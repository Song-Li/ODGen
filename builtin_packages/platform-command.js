var childProcess = require('child_process'); 

module.exports = {
	exec: function(cmd, callback){
		return childProcess.exec(cmd, callback);
	}
}
