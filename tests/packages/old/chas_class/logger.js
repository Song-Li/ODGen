const process = require("process")
const util = require('util')

var Logger = (function() {
    let LevelNames = ["_INVALID", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"];

    let LogLevels = {};

    LevelNames.forEach((name, index, _arr) => {LogLevels[name] = index})

    let LogLevel = LogLevels[process.env['LOG_LEVEL']] || LogLevels.DEBUG

    let do_log = (level_name) => {
        return (message) => {
            console.log("["+level_name + "] " +
                        util.format(message));
        }
    }

    let dont_log = (_message) => {}

    LevelNames.forEach((name, index, _arr) => {
        if (index >= LogLevel) {
            this[name] = do_log(name)
        } else {
            this[name] = dont_log
        }
    })

    this.LogLevels = LogLevels

    return this
})();

module.exports = Logger
