var fs = require('fs');
var array = fs.readFileSync('./builtin.list').toString().split("\n");
var module_template = "module.exports = {\nEXPORT_FUNC}\n";
for(i in array) {
  if(array[i].length > 0){
    var cur_module = require(array[i]);
    var cur_module_src = module_template;
    for (k in cur_module) {
      if (typeof cur_module[k] === 'function') {
        method_name = k;
        cur_module_src = add_method_to_module(cur_module_src, method_name);
      }
    }
    // remove the marker
    cur_module_src = cur_module_src.replace(",\nEXPORT_FUNC", '\n');
    console.log(cur_module_src);
    fs.writeFile("./generated/" + array[i], cur_module_src, function(err){
        if (err) return console.log(err);
        console.log('Finished generating' + array[i]);
    });
  }
}


function generate_method(method_name) {
  /**
   * generate a blank mathod based on the name
   * Args:
   *  method_name: the name of the method
   */
  var method_template = "function FUNC_NAME(arg1, arg2, arg3, arg4, arg5, arg6) {\n\treturn arg1 + arg2 + arg3 + arg4 + arg5 + arg6;\n}\n";
  return method_template.replace("FUNC_NAME", method_name);
}

function add_method_to_module(cur_module_src, method_name) {
  /**
   * generate a blank module based on the name
   * Args:
   *  cur_module_src: the src of the module
   *  method_name: the name of the method
   */
  // add the src of the method
  cur_method_src = generate_method(method_name);
  cur_module_src = cur_method_src + cur_module_src;
  // export the added method
  new_module_src = cur_module_src.replace('EXPORT_FUNC', method_name + ',\nEXPORT_FUNC')
  return new_module_src;
}
