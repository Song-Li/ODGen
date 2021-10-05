module.exports = function({ types: t }) {
    let interFuncName = '_interopRequireDefault'; 

    const interopVisitor = {
        // Remove the definition of the method '_interopRequireDefault'
        FunctionDeclaration(path){
            let curFuncName = path.node.id.name; 
            if(curFuncName === interFuncName) path.remove();
        }, 
        // Replace the importing with "_interopRequireDefault()" invocation.
        CallExpression(path){
            let invocName = path.node.callee.name; 
            if(invocName !== interFuncName) return; 
            let importedName = path.parentPath.node.id.name;
            let arguExp = path.node.arguments[0];
            path.replaceWith(arguExp);
            let program = path.findParent((path) => path.type === 'Program');
            program.traverse({
                MemberExpression(mPath){
                    let mObject = mPath.node.object; 
                    if(importedName !== mObject.name) return;
                    let mProperty = mPath.node.property;
                    if(mProperty.type !== 'StringLiteral') return;
                    if(mProperty.value !== 'default') return;
                    mPath.replaceWith(mObject);
                }
            }); 
        }, 
        // Replace the property access with keyword default from the _interopRequireDefault
        
    }; 
    return {visitor: interopVisitor};
};
  