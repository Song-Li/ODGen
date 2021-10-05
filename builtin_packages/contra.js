function series(arr, cb) {
    // for now, arr is a arr
    var len = arr.length;
    for (var i = 0;i < len;++ i){
        arr[i](cb);
    }
}
module.exports = {
    series: series
}