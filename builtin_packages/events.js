module.exports = {
    EventEmitter: function(options){
    }
}
module.exports.EventEmitter.prototype.addListener = function (eventName, listener){};
module.exports.EventEmitter.prototype.emit = function (eventName, ...args){};
module.exports.EventEmitter.prototype.eventNames = function (){};
module.exports.EventEmitter.prototype.getMaxListeners = function (){};
module.exports.EventEmitter.prototype.listenerCount = function (eventName){};
module.exports.EventEmitter.prototype.listeners = function (eventName){};
module.exports.EventEmitter.prototype.off = function (eventName, listener){};
module.exports.EventEmitter.prototype.on = function (eventName, listener){};
module.exports.EventEmitter.prototype.once = function (eventName, listener){};
module.exports.EventEmitter.prototype.prependListener = function (eventName, listener){};
module.exports.EventEmitter.prototype.prependOnceListener = function (eventName, listener){};
module.exports.EventEmitter.prototype.removeAllListeners = function (eventName){};
module.exports.EventEmitter.prototype.removeListener = function (eventName, listener){};
module.exports.EventEmitter.prototype.setMaxListeners = function (n){};
module.exports.EventEmitter.prototype.rawListeners = function (eventName){};
module.exports.EventEmitter.on = function (emitter, event, options){};
module.exports.EventEmitter.once = function (emitter, event, options){};
module.exports.EventEmitter.listenerCount = function (emitter, event){};
module.exports.EventEmitter.getEventListener = function (emitter, name){};
global.Events = function(type, eventInitDict){};
global.EventTarget = function(){};