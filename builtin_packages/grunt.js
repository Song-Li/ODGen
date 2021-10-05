module.exports = {
    util: {
        _: {
            each: function(array, cb){
                for (let elem of array){
                    cb(elem);
                }
            }
        }
    }
};