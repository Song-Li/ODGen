#!/usr/bin/env node

// setup

var outputStyle; // 'php' or 'c'
var delimiter; // '\t' or ','

const path = require('path');
const fs = require('fs');
const esprima = require('esprima');
const os = require('os');
const ansicolor = require('ansicolor').nice;
const Readable = require('stream').Readable;
const program = require('commander');
program
    .version('0.12.2')
    .usage('<filename or package name> [options]')
    .description('A tool that generates JavaScript AST in Joern compatible CSV format.\n\n' +
        'You can choose a filename or package name as input. Use "-" to accept stdin.')
    .arguments('<filename or package name>')
    .action(function (input) {
        this.input = input;
    })
    .option('-o, --output <path>', 'Specify an output directory. Defaults to current working directory. ' +
        'If input is stdin, defaults to stdout.')
    .option('-n, --start <number>', 'Specify what number the node numbers start from.')
    .option('-s, --search [path]', "Search a package from the path. " +
        "If it doesn't exist, it will follow Node.js's searching strategy. " +
        "Use this option if you give a package name instead of a file name.")
    .option('--style <php/c>', 'Output style. You can choose from "php" and "c".', 'php')
    .option('--delimiter <comma/tab>', 'Delimiter of the output. ' +
        'You can choose from "comma" and "tab".', 'tab')
    .option('-e, --expression', 'Indicate that the input is an expression');

function invalidArguments() {
    console.error('Invalid arguments: %s\nSee --help for a list of available commands.', program.args.join(' '));
    process.exit(1);
}

program.parse(process.argv);

// initialization

var sourceCode = ""; // source code being analyzed
var nodeIdCounter;
var nodes = [];

switch (program.style.toLowerCase()){
    case 'php':
        outputStyle = 'php';
        nodeIdCounter = 0;
        break;
    case 'c':
        outputStyle = 'c';
        nodeIdCounter = 1;
        break;
    default:
        invalidArguments();
        break;
}
switch (program.delimiter.toLowerCase()){
    case 'tab':
        delimiter = '\t';
        break;
    case 'comma':
        delimiter = ',';
        break;
    default:
        invalidArguments();
        break;
}
if (program.start !== undefined){
    nodeIdCounter = parseInt(program.start);
}

var dirname = program.input;
var filename = "";

var requiredModules = new Set(),
    analyzedModules = [];
const builtInModules = require('module').builtinModules;

var stdoutMode = false;
if (program.output ==='-' || (program.input === '-' && program.output === undefined)){
    stdoutMode = true;
}

// write csv headers

var csvHead1PHP = `id:ID\tlabels:label\ttype\tflags:string[]\tlineno:int\tcode\tchildnum:int\tfuncid:int\tclassname\tnamespace\tendlineno:int\tname\tdoccomment\n`.replace(/\t/g, delimiter);
var csvHead1C = `command\tkey\ttype\tcode\tlocation\tfunctionId\tchildNum\tisCFGNode\toperator\tbaseType\tcompleteType\tidentifier\n`.replace(/\t/g, delimiter);
var csvHead2PHP = `start:START_ID\tend:END_ID\ttype:TYPE\n`.replace(/\t/g, delimiter);
var csvHead2C = `start\tend\ttype\tvar\n`.replace(/\t/g, delimiter);
var nodesStream = new Readable();
var relsStream = new Readable();
if (stdoutMode){
    // output to stdout
    var nodesString = '', relsString = '';
    nodesStream.on('data', (chunk) => {
        nodesString += chunk;
    });
    relsStream.on('data', (chunk) => {
        relsString += chunk;
    });
    var stdout = console.log;
    console.log = console.error;
    relsStream.on('end', () => {
        stdout(nodesString);
        stdout(relsString);
    });
} else {
    program.output = program.output || '.';
    // output to files
    nodesStream.pipe(fs.createWriteStream(path.resolve(program.output, 'nodes.csv')));
    relsStream.pipe(fs.createWriteStream(path.resolve(program.output, outputStyle == 'php' ? 'rels.csv' : 'edges.csv')));
}
var parentOf;
if (outputStyle == 'php') {
    nodesStream.push(csvHead1PHP);
} else if (outputStyle == 'c') {
    nodesStream.push(csvHead1C);
}
if (outputStyle == 'php') {
    relsStream.push(csvHead2PHP);
    parentOf = 'PARENT_OF';
} else if (outputStyle == 'c') {
    relsStream.push(csvHead2C);
    parentOf = 'IS_AST_PARENT';
}

// helper functions

function getCode(node, sourceCode) {
    /* get corresponding source code string of a node */
    if (node.range) {
        return sourceCode.substr(node.range[0], node.range[1] - node.range[0]).replace(/\n/g, '');
    } else {
        return null;
    }
};

function getParameterList(node) {
    /* get argument list of a function call */
    let p = [];
    if (node.params) {
        for (var i of node.params) {
            p.push(i.name);
        }
    }
    return p.join(', ');
};

function getFunctionDef(node) {
    /* get the line of code of a function call */
    let pl = getParameterList(node);
    let id = node.id ? node.id.name : '[anonymous]';
    return id + ' (' + pl + ')';
};

const searchModule = require('./search.js').searchModule;
const searchMain = require('./search.js').searchMain;

// convert every node in AST

function dfs(currentNode, currentId, parentId, childNum, currentFunctionId, extra) {
    if (currentNode == null) return "";
    console.log(`Current node: ${currentId.toString().green.bright} ${currentNode.type.toString().bgDarkGray.white} (line: ${currentNode.loc ? currentNode.loc.start.line : '?'}, parent: ${parentId}, funcid: ${currentFunctionId})`);
    let childNumberCounter = 0;
    let vNodeId, vNodeName, vNodeChildNumberCounter = 0;
    let ctype, phptype, phpflag;
    let prevFunctionId;
    let blockExtra;
    // switch (currentNode.constructor.name){
    /*fs.appendFile('./out.dat', currentNode.type + '\n', function(err) {
        if (err) return console.log(err);
    });
    */
    let comment;
    if (currentNode.leadingComments){
        let comments = [];
        for (let c of currentNode.leadingComments){
            comments.push(c.value.trim());
        }
        comment = comments.join('\n');
    }
    comment = (extra ? extra.comment : undefined) || comment;
    switch (currentNode.type) {
        // case 'Script':
        // case 'Module':
        case 'Program':
            prevFunctionId = currentFunctionId;
            if (outputStyle == 'c') {
                for (var child of currentNode.body) {
                    nodeIdCounter++;
                    childNumberCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(child, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, null);
                }
            } else if (outputStyle == 'php') {
                currentFunctionId = currentId;
                // make CFG_FUNC_ENTRY artificial node
                nodeIdCounter++;
                let vCFGFuncEntryId = nodeIdCounter;
                relsStream.push([currentId, vCFGFuncEntryId, 'ENTRY'].join(delimiter) + '\n');
                nodes[vCFGFuncEntryId] = {
                    label: 'Artificial',
                    type: 'CFG_FUNC_ENTRY',
                    name: filename,
                    funcId: currentFunctionId
                };
                console.log(`Make ${nodeIdCounter.toString().green.bright} ${'CFG_FUNC_ENTRY'.lightRed.bright} Artificial node`);
                // make CFG_FUNC_EXIT artificial node
                nodeIdCounter++;
                let vCFGFuncExitId = nodeIdCounter;
                relsStream.push([currentId, vCFGFuncExitId, 'EXIT'].join(delimiter) + '\n');
                nodes[vCFGFuncExitId] = {
                    label: 'Artificial',
                    type: 'CFG_FUNC_EXIT',
                    name: filename,
                    funcId: currentFunctionId
                };
                console.log(`Make ${nodeIdCounter.toString().green.bright} ${'CFG_FUNC_EXIT'.lightRed.bright} Artificial node`);
                // make AST_STMT_LIST virtual node
                nodeIdCounter++;
                let vASTStmtListId = nodeIdCounter;
                relsStream.push([currentId, vASTStmtListId, parentOf].join(delimiter) + '\n');
                nodes[vASTStmtListId] = {
                    label: 'AST_V',
                    type: 'AST_STMT_LIST',
                    childNum: childNum,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                childNumberCounter = 0;
                for (var child of currentNode.body) {
                    nodeIdCounter++;
                    blockExtra = {
                        childNumberCounter: childNumberCounter
                    };
                    relsStream.push([vASTStmtListId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(child, nodeIdCounter, vASTStmtListId, childNumberCounter, currentFunctionId, blockExtra);
                    childNumberCounter = blockExtra.childNumberCounter;
                    childNumberCounter++;
                }
            }
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_TOPLEVEL',
                phpflag: 'TOPLEVEL_FILE',
                name: filename,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                // childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: prevFunctionId
            };
            break;
        case 'VariableDeclaration':
            if (outputStyle == 'c') {
                for (var child of currentNode.declarations) {
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(child, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, null, null);
                    childNumberCounter++;
                }
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    ctype: 'IdentifierDeclStatement',
                    kind: currentNode.kind,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId
                };
            } else if (outputStyle == 'php' && extra && extra.parentType == 'ForStatement') {
                for (var child of currentNode.declarations) {
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(child, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, {
                        kind: currentNode.kind,
                        comment: comment
                    });
                    childNumberCounter++;
                }
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_EXPR_LIST',
                    kind: currentNode.kind,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            } else if (outputStyle == 'php') {
                // Make its children its parent's children
                // Let's assume its parent is a BlockStatement node, which provides an 'extra' information,
                // otherwise the script can only handle one variable declaration.
                if (currentNode.declarations.length >= 1) {
                    if (extra && 'childNumberCounter' in extra) {
                        // console.log(`Got extra: ${JSON.stringify(extra)}`);
                        let firstChildFlag = true,
                            flattenedId;
                        for (var child of currentNode.declarations) {
                            if (firstChildFlag) {
                                firstChildFlag = false;
                                flattenedId = currentId;
                            } else {
                                nodeIdCounter++;
                                flattenedId = nodeIdCounter;
                                extra.childNumberCounter++;
                                relsStream.push([parentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                            }
                            dfs(child, flattenedId, parentId, extra.childNumberCounter, currentFunctionId, {
                                kind: currentNode.kind,
                                comment: comment
                            });
                        }
                        break;
                    } else {
                        console.error("Situation cannot be handled: VariableDeclaration with more than one children but not under a BlockStatment or no extra information");
                        console.error(`Parent ID: ${parentId}, extra: ${JSON.stringify(extra)}`);
                    }
                }
                // dfs(currentNode.declarations[0], currentId, parentId, childNum, currentFunctionId, null);
            }
            break;
        case 'VariableDeclarator':
            if (outputStyle == 'c') {
                nodeIdCounter++;
                childNumberCounter = 0;
                let vVarTypeId = nodeIdCounter;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[vVarTypeId] = {
                    label: 'AST_V',
                    type: 'IdentifierDeclType',
                    code: 'any',
                    childNum: 0,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                nodeIdCounter++;
                relsStream.push([vVarTypeId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.id, nodeIdCounter, vVarTypeId, 0, currentFunctionId, {
                    doNotUseVar: true
                });
                if (currentNode.init) {
                    nodeIdCounter++;
                    childNumberCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.init, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, null);
                }
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    ctype: 'IdentifierDecl',
                    phptype: 'AST_ASSIGN',
                    childNum: childNum,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId
                };
            } else if (outputStyle == 'php') {
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.id, nodeIdCounter, currentId, 0, currentFunctionId, {
                    doNotUseVar: false,
                    kind: (extra && extra.kind) ? extra.kind : null
                });
                if (currentNode.init) {
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.init, nodeIdCounter, currentId, 1, currentFunctionId, null);
                }
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    ctype: 'IdentifierDecl',
                    operator: '=',
                    phptype: 'AST_ASSIGN',
                    phpflag: phpflag,
                    childNum: childNum,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            break;
        case 'UpdateExpression':
            switch (currentNode.operator) {
                case '++':
                    phptype = currentNode.prefix ? 'AST_PRE_INC' : 'AST_POST_INC';
                    break;
                case '--':
                    phptype = currentNode.prefix ? 'AST_PRE_DEC' : 'AST_POST_DEC';
                    break;
            }
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.argument, nodeIdCounter, currentId, 0, currentFunctionId, null);
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: phptype,
                operator: currentNode.operator || null,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'UnaryExpression':
            if (outputStyle == 'php' && (
                currentNode.operator == 'typeof' || currentNode.operator == 'delete'
            )) {
                // converts "typeof foo" to "gettype(foo)" / "delete foo" to "unset(foo)"
                let phpFuncName;
                if (currentNode.operator == 'typeof'){
                    phpFuncName = 'gettype';
                    phpflag = 'JS_TYPEOF';
                } else if (currentNode.operator == 'delete'){
                    phpFuncName = 'unset';
                    phpflag = 'JS_DELETE';
                }
                // make the AST_NAME virtual node (childnum = 0)
                nodeIdCounter++;
                let vAstNameId = nodeIdCounter;
                relsStream.push([currentId, vAstNameId, parentOf].join(delimiter) + '\n');
                nodes[vAstNameId] = {
                    label: 'AST_V',
                    phptype: 'AST_NAME',
                    phpflag: 'NAME_NOT_FQ',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                // make the string virtual node ('gettype')
                nodeIdCounter++;
                let vAstGettypeStringId = nodeIdCounter;
                relsStream.push([vAstNameId, vAstGettypeStringId, parentOf].join(delimiter) + '\n');
                nodes[vAstGettypeStringId] = {
                    label: 'AST_V',
                    phptype: 'string',
                    code: phpFuncName,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                // make the AST_ARG_LIST virtual node (childnum = 1)
                nodeIdCounter++;
                let vAstArgListId = nodeIdCounter;
                relsStream.push([currentId, vAstArgListId, parentOf].join(delimiter) + '\n');
                nodes[vAstArgListId] = {
                    label: 'AST_V',
                    phptype: 'AST_ARG_LIST',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 1,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                // goto the argument
                nodeIdCounter++;
                relsStream.push([vAstArgListId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.argument, nodeIdCounter, vAstArgListId, 0, currentFunctionId, null);
                // finally write the converted AST_CALL node
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_CALL',
                    phpflag: phpflag,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            } else {
                switch (currentNode.operator) {
                    case '!':
                        phpflag = 'UNARY_BOOL_NOT';
                        break;
                    case '~':
                        phpflag = 'UNARY_BITWISE_NOT';
                        break;
                    case '+':
                        phpflag = 'UNARY_PLUS';
                        break;
                    case '-':
                        phpflag = 'UNARY_MINUS';
                        break;
                }
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.argument, nodeIdCounter, currentId, 0, currentFunctionId, null);
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_UNARY_OP',
                    phpflag: phpflag,
                    operator: currentNode.operator || null,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            break;
        case 'AwaitExpression':
        case 'SpreadElement':
        case 'YieldExpression':
            phptype = 'AST_YIELD';
            switch (currentNode.type) {
                case 'AwaitExpression':
                    phpflag = 'JS_AWAIT_EXPRESSION';
                    break;
                case 'SpreadElement':
                    phpflag = 'JS_SPREAD_ELEMENT';
                    break;
                case 'YieldExpression':
                    phpflag = 'JS_YIELD';
                    if (this.delegate) phptype = 'AST_YIELD_FROM';
                    break;
            }
            // console.log(`  Warning: uncompleted support for ${currentNode.type}.`);
            if (currentNode.argument) {
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.argument, nodeIdCounter, currentId, 0, currentFunctionId, null);
            } else {
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                // if argument is null, insert a NULL node
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: phptype,
                phpflag: phpflag,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'BinaryExpression':
        case 'LogicalExpression':
        case 'AssignmentExpression':
        case 'AssignmentPattern':
            ctype = null;
            phptype = null;
            phpflag = null;
            if (currentNode.type == 'AssignmentExpression') {
                ctype = 'AssignmentExpression';
                switch (currentNode.operator) {
                    case '=':
                        phptype = 'AST_ASSIGN';
                        break;
                    case '+=':
                        phptype = 'AST_ASSIGN_OP';
                        phpflag = 'BINARY_ADD';
                        break;
                    case '-=':
                        phptype = 'AST_ASSIGN_OP';
                        phpflag = 'BINARY_SUB';
                        break;
                    case '*=':
                        phptype = 'AST_ASSIGN_OP';
                        phpflag = 'BINARY_MUL';
                        break;
                    case '/=':
                        phptype = 'AST_ASSIGN_OP';
                        phpflag = 'BINARY_DIV';
                        break;
                    default:
                        phptype = 'AST_ASSIGN_OP';
                        break;
                }
            } else if (currentNode.type == 'BinaryExpression') {
                phptype = 'AST_BINARY_OP';
                switch (currentNode.operator) {
                    case '+':
                        ctype = 'AdditiveExpression';
                        phpflag = 'BINARY_ADD';
                        break;
                    case '-':
                        ctype = 'AdditiveExpression';
                        phpflag = 'BINARY_SUB';
                        break;
                    case '*':
                        ctype = 'MultiplicativeExpression';
                        phpflag = 'BINARY_MUL';
                        break;
                    case '/':
                        ctype = 'MultiplicativeExpression';
                        phpflag = 'BINARY_DIV';
                        break;
                    case '==':
                        phpflag = 'BINARY_IS_EQUAL';
                        break;
                    case '!=':
                        phpflag = 'BINARY_IS_NOT_EQUAL';
                        break;
                    case '===':
                        phpflag = 'BINARY_IS_IDENTICAL';
                        break;
                    case '!==':
                        phpflag = 'BINARY_IS_NOT_IDENTICAL';
                        break;
                    case '<':
                        phpflag = 'BINARY_IS_SMALLER';
                        break;
                    case '<':
                        phpflag = 'BINARY_IS_GREATER';
                        break;
                    case '>=':
                        phpflag = 'BINARY_IS_GREATER_OR_EQUAL';
                        break;
                    case '<=':
                        phpflag = 'BINARY_IS_SMALLER_OR_EQUAL';
                        break;
                    case '&':
                        phpflag = 'BINARY_BITWISE_AND';
                        break;
                    case '|':
                        phpflag = 'BINARY_BITWISE_OR';
                        break;
                    case '^':
                        phpflag = 'BINARY_BITWISE_XOR';
                        break;
                }
            } else if (currentNode.type == 'LogicalExpression') {
                phptype = 'AST_BINARY_OP';
                switch (currentNode.operator) {
                    case '||':
                        phpflag = 'BINARY_BOOL_OR';
                        break;
                    case '&&':
                        phpflag = 'BINARY_BOOL_AND';
                        break;
                }
            } else if (currentNode.type == 'AssignmentPattern') {
                phptype = 'AST_ASSIGN';
                phpflag = 'JS_ASSIGNMENT_PATTERN';
            }
            // left
            nodeIdCounter++;
            childNumberCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.left, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // right
            nodeIdCounter++;
            childNumberCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.right, nodeIdCounter, currentId, 1, currentFunctionId, null);

            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                ctype: ctype,
                phptype: phptype,
                phpflag: phpflag,
                operator: currentNode.operator || null,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'Literal':
            let phpLiteralType = typeof(currentNode.value);
            if (outputStyle == 'php' && (phpLiteralType == 'boolean' || currentNode.value == null)) {
                // true, false or null
                nodeIdCounter++;
                let vNameId = nodeIdCounter;
                relsStream.push([currentId, vNameId, parentOf].join(delimiter) + '\n');
                nodes[vNameId] = {
                    label: 'AST_V',
                    type: currentNode.type,
                    phptype: 'AST_NAME',
                    phpflag: 'NAME_NOT_FQ',
                    code: currentNode.raw,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    funcId: currentFunctionId,
                };
                nodeIdCounter++;
                let vTrueFalseId = nodeIdCounter;
                relsStream.push([vNameId, vTrueFalseId, parentOf].join(delimiter) + '\n');
                nodes[vTrueFalseId] = {
                    label: 'AST_V',
                    type: currentNode.type,
                    phptype: 'string',
                    code: currentNode.raw,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    funcId: currentFunctionId,
                };
                nodes[currentId] = {
                    label: 'AST_V',
                    type: currentNode.type,
                    phptype: 'AST_CONST',
                    code: currentNode.raw,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            } else {
                let code;
                if (currentNode.regex) {
                    // regular expression
                    phpLiteralType = 'string';
                    phpflag = 'JS_REGEXP';
                    // replace slashes with double slashes
                    code = '/' + currentNode.regex.pattern + '/' + currentNode.regex.flags;
                } else if (phpLiteralType === 'number') {
                    if (Number.isInteger(currentNode.value))
                        phpLiteralType = 'integer';
                    else
                        phpLiteralType = 'double';
                    code = currentNode.raw;
                } else if (phpLiteralType === 'string'){
                    let quoted = currentNode.raw.match(/^'(.*)'$/) || currentNode.raw.match(/^"(.*)"$/) || ['', ''];
                    code = quoted[1];
                }
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    ctype: 'PrimaryExpression',
                    phptype: phpLiteralType,
                    phpflag: phpflag || '',
                    code: code,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    childNum: childNum,
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            break;
        case 'FunctionExpression':
        case 'FunctionDeclaration':
        case 'ArrowFunctionExpression':
            prevFunctionId = currentFunctionId;
            currentFunctionId = currentId;
            if (outputStyle == 'c') {
                // make FunctionDef virtual node
                nodeIdCounter++;
                let vFunctionDefId = nodeIdCounter;
                relsStream.push([currentId, vFunctionDefId, parentOf].join(delimiter) + '\n');
                // body
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([vFunctionDefId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.body, nodeIdCounter, vFunctionDefId, 0, currentFunctionId, null);
                // returnType
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'ReturnType',
                    code: 'any',
                    childNum: 1,
                    funcId: currentFunctionId
                };
                // id
                if (currentNode.id) {
                    nodeIdCounter++;
                    childNumberCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.id, nodeIdCounter, vFunctionDefId, 2, currentFunctionId, null);
                }
                // params
                // Make a virtual node
                nodeIdCounter++;
                childNumberCounter++;
                vNodeId = nodeIdCounter;
                relsStream.push([vFunctionDefId, vNodeId, parentOf].join(delimiter) + '\n');
                vNodeChildNumberCounter = 0;
                for (param of currentNode.params) {
                    // write the Parameter virtual node
                    nodeIdCounter++;
                    let vParameterId = nodeIdCounter;
                    relsStream.push([vNodeId, vParameterId, parentOf].join(delimiter) + '\n');
                    nodes[vParameterId] = {
                        label: 'AST_V',
                        type: 'Parameter',
                        childNum: vNodeChildNumberCounter,
                        code: param.name || null,
                        funcId: currentFunctionId
                    };
                    vNodeChildNumberCounter++;
                    // write the ParameterType virtual node
                    nodeIdCounter++;
                    relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    nodes[nodeIdCounter] = {
                        label: 'AST_V',
                        type: 'ParameterType',
                        code: 'any',
                        childNum: 0,
                        funcId: currentFunctionId
                    };
                    // go to the parameter Identifier node
                    nodeIdCounter++;
                    relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(param, nodeIdCounter, vParameterId, 1, currentFunctionId, null);
                }
                // Write the params virtual node
                nodes[vNodeId] = {
                    label: 'AST_V',
                    type: 'FunctionDeclarationParams',
                    ctype: 'ParameterList',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 3,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getParameterList(currentNode),
                    funcId: currentFunctionId
                };
                // Write the FunctionDef virtual node
                nodes[vFunctionDefId] = {
                    label: 'AST_V',
                    type: currentNode.type,
                    ctype: 'FunctionDef',
                    code: getFunctionDef(currentNode),
                    childNum: 0,
                    funcId: currentFunctionId
                };
                // Finally, write the FunctionDeclaration itself
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    ctype: 'Function',
                    code: currentNode.id ? currentNode.id.name : null,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    // code: getCode(currentNode, sourceCode),
                    funcId: prevFunctionId, // function itself does not use functionId
                    comment: comment,
                    loc: currentNode.loc
                };
            } else if (outputStyle == 'php') {
                phptype = null;
                phpflag = null;
                // make CFG_FUNC_ENTRY artificial node
                nodeIdCounter++;
                let vCFGFuncEntryId = nodeIdCounter;
                relsStream.push([currentId, vCFGFuncEntryId, 'ENTRY'].join(delimiter) + '\n');
                nodes[vCFGFuncEntryId] = {
                    label: 'Artificial',
                    type: 'CFG_FUNC_ENTRY',
                    funcId: currentFunctionId
                };
                console.log(`Make ${nodeIdCounter.toString().green.bright} ${'CFG_FUNC_ENTRY'.lightRed.bright} Artificial node`);
                // make CFG_FUNC_EXIT artificial node
                nodeIdCounter++;
                let vCFGFuncExitId = nodeIdCounter;
                relsStream.push([currentId, vCFGFuncExitId, 'EXIT'].join(delimiter) + '\n');
                nodes[vCFGFuncExitId] = {
                    label: 'Artificial',
                    type: 'CFG_FUNC_EXIT',
                    funcId: currentFunctionId
                };
                console.log(`Make ${nodeIdCounter.toString().green.bright} ${'CFG_FUNC_EXIT'.lightRed.bright} Artificial node`);
                // id, childnum = 0
                if (currentNode.id) {
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.id, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, {
                        doNotUseVar: true
                    });
                    phptype = 'AST_FUNC_DECL';
                } else {
                    // anonymous function, or method in a class
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    nodes[nodeIdCounter] = {
                        label: 'AST',
                        type: 'string',
                        code: (extra && extra.methodName) ? extra.methodName : '{anon}',
                        childNum: childNumberCounter,
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        funcId: currentFunctionId
                    };
                    if (extra && extra.methodName) {
                        phptype = 'AST_METHOD';
                        phpflag = 'MODIFIER_PUBLIC';
                    } else {
                        phptype = 'AST_CLOSURE';
                    }
                }
                childNumberCounter++;
                // NULL node, childnum = 1
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST',
                    type: 'NULL',
                    childNum: childNumberCounter,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    funcId: currentFunctionId
                };
                childNumberCounter++;
                // params, childnum = 2
                // Make a virtual node
                nodeIdCounter++;
                vNodeId = nodeIdCounter;
                relsStream.push([currentId, vNodeId, parentOf].join(delimiter) + '\n');
                vNodeChildNumberCounter = 0;
                for (param of currentNode.params) {
                    function addParam(param){
                        // write the Parameter virtual node
                        nodeIdCounter++;
                        let vParameterId = nodeIdCounter;
                        relsStream.push([vNodeId, vParameterId, parentOf].join(delimiter) + '\n');
                        nodes[vParameterId] = {
                            label: 'AST_V',
                            type: 'Parameter',
                            phptype: 'AST_PARAM',
                            phpflag: phpflag,
                            childNum: vNodeChildNumberCounter,
                            code: param.name || null,
                            lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                            funcId: currentFunctionId
                        };
                        // write the 1st NULL virtual node (childnum = 0)
                        nodeIdCounter++;
                        relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                        nodes[nodeIdCounter] = {
                            label: 'AST_V',
                            type: 'ParameterType',
                            phptype: 'NULL',
                            childNum: 0,
                            code: 'any',
                            lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                            funcId: currentFunctionId
                        };
                        if (param.type == 'Identifier') { // no default value
                            // go to the parameter Identifier node (childnum = 1)
                            nodeIdCounter++;
                            relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                            dfs(param, nodeIdCounter, vParameterId, 1, currentFunctionId, {
                                doNotUseVar: true
                            });
                            // write the 2nd NULL virtual node (childnum = 2)
                            nodeIdCounter++;
                            relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                            nodes[nodeIdCounter] = {
                                label: 'AST_V',
                                // type: 'ParameterType',
                                phptype: 'NULL',
                                childNum: 2,
                                code: 'any',
                                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                                funcId: currentFunctionId
                            };
                        } else if (param.type == 'AssignmentPattern') { // with default value
                            // go to the parameter Identifier node (childnum = 1)
                            nodeIdCounter++;
                            relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                            dfs(param.left, nodeIdCounter, vParameterId, 1, currentFunctionId, {
                                doNotUseVar: true
                            });
                            // write the 2nd NULL virtual node (childnum = 2)
                            nodeIdCounter++;
                            relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                            dfs(param.right, nodeIdCounter, vParameterId, 2, currentFunctionId, {
                                doNotUseVar: true
                            });
                        } else if (param.type == 'RestElement') { // no default value
                            // go to the parameter Identifier node (childnum = 1)
                            nodeIdCounter++;
                            relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                            dfs(param.argument, nodeIdCounter, vParameterId, 1, currentFunctionId, {
                                doNotUseVar: true
                            });
                            // write the 2nd NULL virtual node (childnum = 2)
                            nodeIdCounter++;
                            relsStream.push([vParameterId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                            nodes[nodeIdCounter] = {
                                label: 'AST_V',
                                // type: 'ParameterType',
                                phptype: 'NULL',
                                childNum: 2,
                                code: 'any',
                                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                                funcId: currentFunctionId
                            };
                        }
                        // finally update the childnum counter
                        vNodeChildNumberCounter++;
                    }
                    if (param.type == 'RestElement'){
                        // rest parameter (variable length arguments)
                        phpflag = 'PARAM_VARIADIC';
                    } else if (param.type == 'ObjectPattern' || param.type == 'ArrayPattern' || param.type == 'AssignmentPattern'){
                        console.log(`  Warning: uncompleted support for ${currentNode.type} as a function parameter, may have unexpected errors.`);
                        let target = param;
                        if (param.type == 'AssignmentPattern'){
                            target = param.left;
                        }
                        if (target.type == 'ObjectPattern'){
                            for (let prop of target.properties){
                                addParam(prop.key);
                            }
                        } else if (target.type == 'ArrayPattern'){
                            for (let elem of target.elements){
                                addParam(elem);
                            }
                        }
                    } else {
                        addParam(param);
                    }
                }
                // Write the params virtual node (childnum = 2)
                nodes[vNodeId] = {
                    label: 'AST_V',
                    type: 'FunctionDeclarationParams',
                    ctype: 'ParameterList',
                    phptype: 'AST_PARAM_LIST',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 2,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getParameterList(currentNode),
                    funcId: currentFunctionId
                };
                childNumberCounter++;
                // NULL node, childnum = 3 (anonymous function only)
                if (!currentNode.id && !(extra && extra.methodName)) {
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    nodes[nodeIdCounter] = {
                        label: 'AST',
                        type: 'NULL',
                        childNum: childNumberCounter,
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        funcId: currentFunctionId
                    };
                    childNumberCounter++;
                }
                // body (statement list), childnum = 3 (named), 4 (anonymous)
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                if (currentNode.body.type == 'BlockStatement'){
                    dfs(currentNode.body, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, null);
                } else {
                    let vBlockStatementNode = nodeIdCounter;
                    nodeIdCounter++;
                    let vReturnNode = nodeIdCounter;
                    relsStream.push([vBlockStatementNode, vReturnNode, parentOf].join(delimiter) + '\n');
                    nodes[vReturnNode] = {
                        label: 'AST',
                        type: 'ReturnStatement',
                        phptype: 'AST_RETURN',
                        lineLocStart: currentNode.body.loc ? currentNode.body.loc.start.line : null,
                        childNum: 0,
                        lineLocEnd: currentNode.body.loc ? currentNode.body.loc.end.line : null,
                        colLocStart: currentNode.body.loc ? currentNode.body.loc.start.column : null,
                        colLocEnd: currentNode.body.loc ? currentNode.body.loc.end.column : null,
                        code: getCode(currentNode, sourceCode),
                        funcId: currentFunctionId
                    };
                    nodeIdCounter++;
                    let vArgumentNode = nodeIdCounter;
                    relsStream.push([vReturnNode, vArgumentNode, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.body, vArgumentNode, vReturnNode, 0, currentFunctionId, null);
                    nodes[vBlockStatementNode] = {
                        label: 'AST_V',
                        type: 'BlockStatement',
                        phptype: 'AST_STMT_LIST',
                        lineLocStart: currentNode.body.loc ? currentNode.body.loc.start.line : null,
                        lineLocEnd: currentNode.body.loc ? currentNode.body.loc.end.line : null,
                        colLocStart: currentNode.body.loc ? currentNode.body.loc.start.column : null,
                        colLocEnd: currentNode.body.loc ? currentNode.body.loc.end.column : null,
                        childNum: childNumberCounter,
                        funcId: currentFunctionId
                    };
                }
                childNumberCounter++;
                // NULL node, childnum = 4 (named), 5 (anonymous)
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST',
                    type: 'NULL',
                    childNum: childNumberCounter,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    funcId: currentFunctionId
                };
                childNumberCounter++;
                // return type node, childnum = 5
                // This node can be NULL node. Let's ignore it and use a NULL node first.
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST',
                    type: 'NULL',
                    childNum: childNumberCounter,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    funcId: currentFunctionId
                };
                childNumberCounter++;
                // Finally, write the FunctionDeclaration itself
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    ctype: 'Function',
                    phptype: phptype,
                    phpflag: phpflag,
                    code: currentNode.id ? currentNode.id.name : null,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    // code: getCode(currentNode, sourceCode),
                    funcId: prevFunctionId, // function itself does not use functionId
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            break;
        case 'ClassBody':
            if (outputStyle == 'php') {
                prevFunctionId = currentFunctionId;
                currentFunctionId = currentId;
                // make AST_TOPLEVEL virtual node, as the new parent node
                // nodeIdCounter++; // do not write this
                let vAstToplevelClass = nodeIdCounter;
                nodes[vAstToplevelClass] = {
                    label: 'AST_V',
                    type: 'AST_TOPLEVEL',
                    phpflag: 'TOPLEVEL_CLASS',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: prevFunctionId
                };
                // make CFG_FUNC_ENTRY artificial node
                nodeIdCounter++;
                let vCFGFuncEntryId = nodeIdCounter;
                relsStream.push([vAstToplevelClass, vCFGFuncEntryId, 'ENTRY'].join(delimiter) + '\n');
                nodes[vCFGFuncEntryId] = {
                    label: 'Artificial',
                    type: 'CFG_FUNC_ENTRY',
                    funcId: currentFunctionId
                };
                console.log(`Make ${nodeIdCounter.toString().green.bright} ${'CFG_FUNC_ENTRY'.lightRed.bright} Artificial node`);
                // make CFG_FUNC_EXIT artificial node
                nodeIdCounter++;
                let vCFGFuncExitId = nodeIdCounter;
                relsStream.push([vAstToplevelClass, vCFGFuncExitId, 'EXIT'].join(delimiter) + '\n');
                nodes[vCFGFuncExitId] = {
                    label: 'Artificial',
                    type: 'CFG_FUNC_EXIT',
                    funcId: currentFunctionId
                };
                console.log(`Make ${nodeIdCounter.toString().green.bright} ${'CFG_FUNC_EXIT'.lightRed.bright} Artificial node`);
                // reserve a node id for AST_STMT_LIST
                nodeIdCounter++;
                let classBodyId = nodeIdCounter;
                // go into the body
                for (b of currentNode.body) {
                    nodeIdCounter++;
                    relsStream.push([classBodyId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    blockExtra = {
                        childNumberCounter: childNumberCounter
                    };
                    dfs(b, nodeIdCounter, classBodyId, childNumberCounter, currentFunctionId, blockExtra);
                    childNumberCounter = blockExtra.childNumberCounter;
                    childNumberCounter++;
                    /*
                        The purpose of childNumberCounter in blockExtra is to make VariableDeclaration
                        child node in the next recursion able to modify its parent's childNumberCounter,
                        so the VariableDeclarator nodes in PHP style can be flattened as if they are
                        BlockStatement's children instead of VariableDeclaration's children.
                    */
                }
                // finally, write the ClassBody node
                relsStream.push([vAstToplevelClass, classBodyId, 'PARENT_OF'].join(delimiter) + '\n');
                nodes[classBodyId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_STMT_LIST',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                currentFunctionId = prevFunctionId
            }
            break;
        case 'BlockStatement':
            ctype = 'CompoundStatement';
            phptype = 'AST_STMT_LIST';
            for (b of currentNode.body) {
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                blockExtra = {
                    childNumberCounter: childNumberCounter
                };
                dfs(b, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, blockExtra);
                childNumberCounter = blockExtra.childNumberCounter;
                childNumberCounter++;
                /*
                    The purpose of childNumberCounter in blockExtra is to make VariableDeclaration
                    child node in the next recursion able to modify its parent's childNumberCounter,
                    so the VariableDeclarator nodes in PHP style can be flattened as if they are
                    BlockStatement's children instead of VariableDeclaration's children.
                */
            }
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                ctype: ctype,
                phptype: phptype,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'SequenceExpression':
            for (e of currentNode.expressions) {
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                let blockExtra = {
                    childNumberCounter: childNumberCounter
                };
                dfs(e, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, blockExtra);
                childNumberCounter = blockExtra.childNumberCounter;
                childNumberCounter++;
                /*
                    The purpose of childNumberCounter in blockExtra is to make VariableDeclaration
                    child node in the next recursion able to modify its parent's childNumberCounter,
                    so the VariableDeclarator nodes in PHP style can be flattened as if they are
                    BlockStatement's children instead of VariableDeclaration's children.
                */
            }
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_EXPR_LIST',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'ReturnStatement':
            nodeIdCounter++;
            childNumberCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            if (currentNode.argument) {
                dfs(currentNode.argument, nodeIdCounter, currentId, 0, currentFunctionId, null);
            } else {
                // insert a NULL node
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    funcId: currentFunctionId
                };
            }
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_RETURN',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'ArrayPattern':
            // console.log(`  Warning: uncompleted support for ${currentNode.type}.`);
        case 'ArrayExpression':
            for (element of currentNode.elements) {
                // make AST_ARRAY_ELEM virtual node
                nodeIdCounter++;
                let vAstArrayElemId = nodeIdCounter;
                relsStream.push([currentId, vAstArrayElemId, parentOf].join(delimiter) + '\n');
                nodes[vAstArrayElemId] = {
                    label: 'AST_V',
                    type: currentNode.type + 'Element',
                    phptype: 'AST_ARRAY_ELEM',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNumberCounter,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                // value
                nodeIdCounter++;
                relsStream.push([vAstArrayElemId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(element, nodeIdCounter, currentId, 0, currentFunctionId, null);
                // key (null)
                nodeIdCounter++;
                relsStream.push([vAstArrayElemId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 1,
                    funcId: currentFunctionId
                };
                childNumberCounter++;
            }
            // Finally, write the ArrayPattern itself
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_ARRAY',
                phpflag: 'JS_ARRAY',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'RestElement':
            console.log(`  Warning: uncompleted support for ${currentNode.type}.`);
            nodeIdCounter++;
            childNumberCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.argument, nodeIdCounter, currentId, 0, currentFunctionId, null);
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'ObjectPattern':
            // console.log(`  Warning: uncompleted support for ${currentNode.type}.`);
        case 'ObjectExpression':
            // vNodeName = currentNode.type + 'Properties';
            // // Make a virtual node
            // // nodeIdCounter++;
            // // childNumberCounter++;
            // // vNodeId = nodeIdCounter;
            // // relsStream.push([currentId, vNodeId, parentOf].join(delimiter)+'\n');
            // // vNodeChildNumberCounter = 0;
            // for (prop of currentNode.properties) {
            //     nodeIdCounter++;
            //     // vNodeChildNumberCounter++;
            //     // relsStream.push([vNodeId, nodeIdCounter, parentOf].join(delimiter)+'\n');
            //     // dfs(param, nodeIdCounter, vNodeId, currentFunctionId, null);
            //     childNumberCounter++;
            //     relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            //     dfs(prop, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // }
            // // Write the virtual node
            // // nodes[vNodeId]=['AST_V',vNodeName,'',currentNode.loc?currentNode.loc.start.line:null,vNodeChildNumberCounter,'','','',currentNode.loc.end.line,'',''];
            // // Finally, write the ObjectPattern itself
            // nodes[currentId] = {
            //     label: 'AST',
            //     type: currentNode.type,
            //     lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
            //     childNum: childNum,
            //     lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
            //     colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
            //     colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
            //     code: getCode(currentNode, sourceCode),
            //     funcId: currentFunctionId
            // };
            if (outputStyle == 'php') {
                for (var prop of currentNode.properties) {
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(prop, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, null);
                    childNumberCounter++;
                }
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_ARRAY',
                    phpflag: 'JS_OBJECT',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    // code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            break;
        case 'Property':
            if (outputStyle == 'php') {
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.value, nodeIdCounter, currentId, 0, currentFunctionId, null);
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.key, nodeIdCounter, currentId, 1, currentFunctionId, {
                    doNotUseVar: true
                });
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_ARRAY_ELEM',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    // code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            break;
        case 'Identifier': {
            let name = currentNode.name;
            let code = getCode(currentNode, sourceCode);
            if (outputStyle == 'c' || (extra && extra.doNotUseVar)) {
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'string',
                    phpflag: (extra ? extra.flag : null) || null,
                    // name: name,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: code,
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            } else {
                // receive the kind information passed from VariableDeclaration via VariableDeclarator
                // then convert kind to PHP flag
                if (extra && extra.kind) {
                    switch (extra.kind) {
                        case 'var':
                            phpflag = 'JS_DECL_VAR';
                            break;
                        case 'let':
                            phpflag = 'JS_DECL_LET';
                            break;
                        case 'const':
                            phpflag = 'JS_DECL_CONST';
                            break;
                    }
                }
                // make AST_VAR virtual node
                let vAstVarId = currentId;
                nodes[vAstVarId] = {
                    label: 'AST_V',
                    type: currentNode.type,
                    phptype: 'AST_VAR',
                    phpflag: phpflag,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                nodeIdCounter++;
                relsStream.push([vAstVarId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                // write the Identifier node
                nodes[nodeIdCounter] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'string',
                    name: name,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: code,
                    funcId: currentFunctionId
                };
            }
            break;
        }
        case 'MethodDefinition':
            // directly go to the value child node
            dfs(currentNode.value, currentId, parentId, childNum, currentFunctionId, {
                methodName: currentNode.key.name
            });
            // console.log(`  Warning: uncompleted support for ${currentNode.type}.`);
            // nodeIdCounter++;
            // childNumberCounter++;
            // relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            // dfs(currentNode.key, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // nodeIdCounter++;
            // childNumberCounter++;
            // relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            // dfs(currentNode.value, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // nodes[currentId] = {
            //     label: 'AST',
            //     type: currentNode.type,
            //     code: currentNode.kind,
            //     lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
            //     childNum: childNum,
            //     lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
            //     colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
            //     colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
            //     funcId: currentFunctionId
            // };
            break;
        case 'ClassExpression':
        case 'ClassDeclaration':
            // console.log(`  Warning: uncompleted support for ${currentNode.type}.`);
            if (outputStyle == 'c') {
                if (currentNode.id) {
                    nodeIdCounter++;
                    childNumberCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.id, nodeIdCounter, currentId, 0, currentFunctionId, null);
                }
                if (currentNode.superClass) {
                    nodeIdCounter++;
                    childNumberCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.superClass, nodeIdCounter, currentId, 0, currentFunctionId, null);
                }
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.body, nodeIdCounter, currentId, 0, currentFunctionId, null);
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    code: currentNode.kind,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
            } else if (outputStyle == 'php') {
                // name/id
                if (currentNode.id) {
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.id, nodeIdCounter, currentId, 0, currentFunctionId, {
                        doNotUseVar: true
                    });
                }
                // docComment, insert a NULL node
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 1,
                    funcId: currentFunctionId
                };
                // extends/superClass
                if (currentNode.superClass) {
                    nodeIdCounter++;
                    let vAstNameId = nodeIdCounter;
                    relsStream.push([currentId, vAstNameId, parentOf].join(delimiter) + '\n');
                    nodes[vAstNameId] = {
                        label: 'AST_V',
                        phptype: 'AST_NAME',
                        phpflag: 'NAME_NOT_FQ',
                        childNum: 2,
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                        colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                        colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                        funcId: currentFunctionId
                    };
                    nodeIdCounter++;
                    relsStream.push([vAstNameId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.superClass, nodeIdCounter, vAstNameId, 0, currentFunctionId, {
                        doNotUseVar: true
                    });
                } else {
                    // no super class, insert a NULL node
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    nodes[nodeIdCounter] = {
                        label: 'AST_V',
                        type: 'NULL',
                        phptype: 'NULL',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        childNum: 2,
                        funcId: currentFunctionId
                    };
                }
                // implements, JavaScript does not support interface, insert a NULL node
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 3,
                    funcId: currentFunctionId
                };
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.body, nodeIdCounter, currentId, 4, currentFunctionId, null);
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_CLASS',
                    code: currentNode.kind,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            break;
        case 'NewExpression':
        case 'CallExpression': {
            phpflag = null;
            vNodeName = currentNode.type + 'Arguments';
            if (currentNode.type == 'NewExpression') phptype = 'AST_NEW';
            else phptype = 'AST_CALL';
            // callee
            if (outputStyle == 'c') {
                nodeIdCounter++; // virtual Callee node
                let vCalleeId = nodeIdCounter;
                relsStream.push([currentId, vCalleeId, parentOf].join(delimiter) + '\n');
                nodes[vCalleeId] = {
                    label: 'AST_V',
                    type: 'Callee',
                    phptype: 'AST_NAME',
                    phpflag: 'NAME_NOT_FQ',
                    childNum: childNumberCounter,
                    // code: currentNode.callee.name || getCode(currentNode.callee, sourceCode) || '',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                nodeIdCounter++; // go to Identifier node
                relsStream.push([vCalleeId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.callee, nodeIdCounter, vCalleeId, 0, currentFunctionId, null);
            } else if (outputStyle == 'php') {
                if (currentNode.callee.type == 'MemberExpression' && currentNode.type != 'NewExpression') {
                    // if it's a member function call, we need to convert it to the PHP format
                    phptype = 'AST_METHOD_CALL';
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.callee.object, nodeIdCounter, currentId, childNumberCounter, currentFunctionId);
                    childNumberCounter++;
                    // go to the method (member) child node
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.callee.property, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, {
                        doNotUseVar: !currentNode.callee.computed
                    });
                } else if (currentNode.callee.type == 'Identifier') {
                    nodeIdCounter++; // virtual Callee node
                    let vAstNameId = nodeIdCounter;
                    relsStream.push([currentId, vAstNameId, parentOf].join(delimiter) + '\n');
                    nodes[vAstNameId] = {
                        label: 'AST_V',
                        phptype: 'AST_NAME',
                        phpflag: 'NAME_NOT_FQ',
                        childNum: childNumberCounter,
                        // code: currentNode.callee.name || getCode(currentNode.callee, sourceCode) || '',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                        colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                        colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                        funcId: currentFunctionId
                    };
                    nodeIdCounter++;
                    relsStream.push([vAstNameId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.callee, nodeIdCounter, currentId, 0, currentFunctionId, {
                        doNotUseVar: true
                    });
                } else {
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.callee, nodeIdCounter, currentId, 0, currentFunctionId, {
                        doNotUseVar: true
                    });
                }
            }
            childNumberCounter++;
            // arguments
            // Make a virtual ArgumentList node
            nodeIdCounter++;
            vNodeId = nodeIdCounter;
            relsStream.push([currentId, vNodeId, parentOf].join(delimiter) + '\n');
            vNodeChildNumberCounter = 0;
            for (argument of currentNode.arguments) {
                if (outputStyle == 'c') {
                    nodeIdCounter++; // virtual Argument node
                    let vArgumentId = nodeIdCounter;
                    relsStream.push([vNodeId, vArgumentId, parentOf].join(delimiter) + '\n');
                    nodes[vArgumentId] = {
                        label: 'AST_V',
                        type: 'Argument',
                        childNum: vNodeChildNumberCounter,
                        code: argument.name || argument.raw || '',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        funcId: currentFunctionId,
                    };
                    nodeIdCounter++; // go to Identifier / Literal node
                    vNodeChildNumberCounter++;
                    relsStream.push([vArgumentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(argument, nodeIdCounter, vArgumentId, 0, currentFunctionId, null);
                } else if (outputStyle == 'php') {
                    nodeIdCounter++; // virtual Argument node
                    relsStream.push([vNodeId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(argument, nodeIdCounter, vNodeId, vNodeChildNumberCounter, currentFunctionId, null);
                }
                vNodeChildNumberCounter++;
            }
            code = getCode(currentNode, sourceCode).match(/\(([^\)]*)\)[^\(\)]*$/);
            code = code ? code[0] : '';
            // Write the virtual ArgumentList node
            nodes[vNodeId] = {
                label: 'AST_V',
                type: vNodeName,
                ctype: 'ArgumentList',
                phptype: 'AST_ARG_LIST',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNumberCounter,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: code,
                funcId: currentFunctionId
            };
            childNumberCounter++;
            // if the callee is 'require', add the required module into the queue
            let modulePath = null;
            if (currentNode.callee && currentNode.callee.name == 'require') {
                if (currentNode.arguments && currentNode.arguments.length >= 1 && currentNode.arguments[0].type == 'Literal') {
                    let moduleName = currentNode.arguments[0].value;
                    if (filename == 'stdin'){
                        modulePath = searchModule(moduleName, process.cwd())[0];
                    } else {
                        modulePath = searchModule(moduleName, filename)[0];
                    }
                    if (modulePath && !requiredModules.has(modulePath)) {
                        requiredModules.add(modulePath);
                    }
                    if (builtInModules.includes(moduleName)) {
                        phpflag = 'JS_REQUIRE_BUILTIN';
                    } else {
                        phpflag = 'JS_REQUIRE_EXTERNAL';
                    }
                } else {
                    console.error(`Invalid require expression: ${getCode(currentNode, sourceCode)}`);
                }
            }
            code = getCode(currentNode, sourceCode);
            if (code.length > 100 || code.includes('\n')) code = '';
            // Finally, write the CallExpression/NewExpression itself
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: phptype,
                phpflag: phpflag,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: code,
                funcId: currentFunctionId,
                name: modulePath,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        }
        case 'SwitchStatement':
            // discriminant
            nodeIdCounter++;
            childNumberCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.discriminant, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // cases
            // Make a virtual node
            nodeIdCounter++;
            vNodeId = nodeIdCounter;
            relsStream.push([currentId, vNodeId, parentOf].join(delimiter) + '\n');
            vNodeChildNumberCounter = 0;
            for (c of currentNode.cases) {
                nodeIdCounter++;
                relsStream.push([vNodeId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(c, nodeIdCounter, vNodeId, vNodeChildNumberCounter, currentFunctionId, null);
                vNodeChildNumberCounter++;
            }
            // Write the virtual node
            nodes[vNodeId] = {
                label: 'AST_V',
                type: 'SwitchStatementCases',
                phptype: 'AST_SWITCH_LIST',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: 1,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId
            };
            // Finally, write the SwitchStatement itself
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_SWITCH',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'SwitchCase':
            // test
            if (currentNode.test) {
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.test, nodeIdCounter, currentId, 0, currentFunctionId, null);
            } else {
                // insert a NULL node
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    funcId: currentFunctionId
                };
            }
            // consequent
            // Make a virtual node
            nodeIdCounter++;
            childNumberCounter++;
            vNodeId = nodeIdCounter;
            relsStream.push([currentId, vNodeId, parentOf].join(delimiter) + '\n');
            vNodeChildNumberCounter = 0;
            // go to consequents
            for (c of currentNode.consequent) {
                nodeIdCounter++;
                blockExtra = {
                    childNumberCounter: vNodeChildNumberCounter
                };
                relsStream.push([vNodeId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(c, nodeIdCounter, vNodeId, vNodeChildNumberCounter, currentFunctionId, blockExtra);
                vNodeChildNumberCounter = blockExtra.childNumberCounter;
                vNodeChildNumberCounter++;
            }
            // Write the virtual node
            nodes[vNodeId] = {
                label: 'AST_V',
                type: 'SwitchCaseConsequents',
                phptype: 'AST_STMT_LIST',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: 1,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId
            };
            // Finally, write the SwitchCase itself
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_SWITCH_CASE',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'WhileStatement':
            // test
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.test, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // body
            makeVirtualNodeForBody(currentNode.body, currentId, 1, currentFunctionId);
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_WHILE',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'WithStatement':
            console.log(`  Warning: uncompleted support for ${currentNode.type}.`);
            // object
            nodeIdCounter++;
            childNumberCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.object, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // body
            nodeIdCounter++;
            childNumberCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.body, nodeIdCounter, currentId, 0, currentFunctionId, null);
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'ForStatement':
            // init
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            if (currentNode.init) {
                dfs(currentNode.init, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, {
                    parentType: 'ForStatement'
                });
            } else {
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNumberCounter,
                    funcId: currentFunctionId
                };
            }
            childNumberCounter++;
            // test
            nodeIdCounter++;
            if (currentNode.test) {
                if (outputStyle == 'c') {
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.test, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, null);
                } else if (outputStyle == 'php') {
                    // make the AST_EXPR_LIST virtual node
                    let vExprListId = nodeIdCounter;
                    relsStream.push([currentId, vExprListId, parentOf].join(delimiter) + '\n');
                    // go to the test child node
                    nodeIdCounter++;
                    relsStream.push([vExprListId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.test, nodeIdCounter, vExprListId, 0, currentFunctionId, {
                        parentType: 'ForStatement'
                    });
                    // write the AST_EXPR_LIST virtual node
                    nodes[vExprListId] = {
                        label: 'AST_V',
                        type: 'SequenceExpression',
                        phptype: 'AST_EXPR_LIST',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        childNum: childNumberCounter,
                        lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                        colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                        colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                        funcId: currentFunctionId
                    };
                }
            } else {
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNumberCounter,
                    funcId: currentFunctionId
                };
            }
            childNumberCounter++;
            // update
            nodeIdCounter++;
            if (currentNode.update) {
                if (outputStyle == 'php' && currentNode.update.type != 'SequenceExpression') {
                    // make the AST_EXPR_LIST virtual node
                    let vExprListId = nodeIdCounter;
                    relsStream.push([currentId, vExprListId, parentOf].join(delimiter) + '\n');
                    // go to the update child node
                    nodeIdCounter++;
                    relsStream.push([vExprListId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.update, nodeIdCounter, vExprListId, 0, currentFunctionId, {
                        parentType: 'ForStatement'
                    });
                    // write the AST_EXPR_LIST virtual node
                    nodes[vExprListId] = {
                        label: 'AST_V',
                        type: 'SequenceExpression',
                        phptype: 'AST_EXPR_LIST',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        childNum: childNumberCounter,
                        lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                        colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                        colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                        funcId: currentFunctionId
                    };
                } else { // C or the update node is already a SequenceExpression node (more than one updates)
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.update, nodeIdCounter, currentId, childNumberCounter, currentFunctionId, {
                        parentType: 'ForStatement'
                    });
                }
            } else {
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNumberCounter,
                    funcId: currentFunctionId
                };
            }
            childNumberCounter++;
            // body
            makeVirtualNodeForBody(currentNode.body, currentId, childNumberCounter, currentFunctionId);
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_FOR',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            childNumberCounter++;
            break;
        case 'ForInStatement':
        case 'ForOfStatement':
            if (outputStyle == 'c') {
                // left
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.left, nodeIdCounter, currentId, 0, currentFunctionId, null);
                // right
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.right, nodeIdCounter, currentId, 1, currentFunctionId, null);
                // body
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.body, nodeIdCounter, currentId, 2, currentFunctionId, null);
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_FOREACH',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                break;
            } else if (outputStyle == 'php') {
                // right (object)
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.right, nodeIdCounter, currentId, 0, currentFunctionId, null);
                if (currentNode.type == 'ForInStatement') {
                    phpflag = 'JS_FOR_IN';
                    // null (value)
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    nodes[nodeIdCounter] = {
                        label: 'AST_V',
                        type: 'NULL',
                        phptype: 'NULL',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        childNum: 1,
                        funcId: currentFunctionId
                    };
                    // left (key)
                    let leftIdentifier;
                    let varphpflag = "";
                    if (currentNode.left.type == 'VariableDeclaration' &&
                        currentNode.left.declarations && currentNode.left.declarations[0]){
                        leftIdentifier = currentNode.left.declarations[0].id;
                        switch (currentNode.left.kind){
                            case 'var':
                                varphpflag = 'JS_DECL_VAR';
                                break;
                            case 'let':
                                varphpflag = 'JS_DECL_LET';
                                break;
                            case 'const':
                                varphpflag = 'JS_DECL_CONST';
                                break;
                        }
                    } else if (currentNode.left.type == 'Identifier'){
                        leftIdentifier = currentNode.left;
                    }
                    if (leftIdentifier != undefined){
                        // make AST_VAR virtual node
                        nodeIdCounter++;
                        let vAstVarId = nodeIdCounter;
                        relsStream.push([currentId, vAstVarId, parentOf].join(delimiter) + '\n');
                        nodes[vAstVarId] = {
                            label: 'AST_V',
                            type: 'VariableDeclarator',
                            phptype: 'AST_VAR',
                            phpflag: varphpflag,
                            lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                            childNum: 2,
                            funcId: currentFunctionId
                        };
                        nodeIdCounter++;
                        relsStream.push([vAstVarId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                        // write the Identifier node
                        nodes[nodeIdCounter] = {
                            label: 'AST',
                            type: 'Identifier',
                            phptype: 'string',
                            name: leftIdentifier.name,
                            lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                            childNum: 0,
                            code: leftIdentifier.name,
                            funcId: currentFunctionId
                        };
                    } else {
                        console.error('Abnormal for loop that program cannot handle.')
                    }
                } else if (currentNode.type == 'ForOfStatement') {
                    phpflag = 'JS_FOR_OF';
                    // left (value)
                    let leftIdentifier;
                    let varphpflag = "";
                    if (currentNode.left.type == 'VariableDeclaration' &&
                        currentNode.left.declarations && currentNode.left.declarations[0]){
                        leftIdentifier = currentNode.left.declarations[0].id;
                        switch (currentNode.left.kind){
                            case 'var':
                                varphpflag = 'JS_DECL_VAR';
                                break;
                            case 'let':
                                varphpflag = 'JS_DECL_LET';
                                break;
                            case 'const':
                                varphpflag = 'JS_DECL_CONST';
                                break;
                        }
                    } else if (currentNode.left.type == 'Identifier'){
                        leftIdentifier = currentNode.left;
                    }
                    if (leftIdentifier != undefined){
                        // make AST_VAR virtual node
                        nodeIdCounter++;
                        let vAstVarId = nodeIdCounter;
                        relsStream.push([currentId, vAstVarId, parentOf].join(delimiter) + '\n');
                        nodes[vAstVarId] = {
                            label: 'AST_V',
                            type: 'VariableDeclarator',
                            phptype: 'AST_VAR',
                            phpflag: varphpflag,
                            lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                            childNum: 1,
                            funcId: currentFunctionId
                        };
                        nodeIdCounter++;
                        relsStream.push([vAstVarId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                        // write the Identifier node
                        nodes[nodeIdCounter] = {
                            label: 'AST',
                            type: 'Identifier',
                            phptype: 'string',
                            name: leftIdentifier.name,
                            lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                            childNum: 0,
                            code: leftIdentifier.name,
                            funcId: currentFunctionId
                        };
                    } else {
                        console.error('Abnormal for loop that program cannot handle.')
                    }
                    // null (key)
                    nodeIdCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    nodes[nodeIdCounter] = {
                        label: 'AST_V',
                        type: 'NULL',
                        phptype: 'NULL',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        childNum: 2,
                        funcId: currentFunctionId
                    };
                }
                // body
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.body, nodeIdCounter, currentId, 3, currentFunctionId, null);
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'AST_FOREACH',
                    phpflag: phpflag,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
        case 'ExpressionStatement':
            if (outputStyle == 'php') { // Ignore this level in PHP
                dfs(currentNode.expression, nodeIdCounter, parentId, childNum, currentFunctionId, {
                    comment: comment
                });
            } else if (outputStyle == 'c') {
                // expression
                nodeIdCounter++;
                childNumberCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.expression, nodeIdCounter, currentId, 0, currentFunctionId, null);
                // directive
                if (currentNode.directive) {
                    nodeIdCounter++;
                    childNumberCounter++;
                    relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(currentNode.directive, nodeIdCounter, currentId, 0, currentFunctionId, null);
                }
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId
                };
            }
            break;
        case 'MemberExpression':
            if (outputStyle == 'php') {
                // object
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.object, nodeIdCounter, currentId, 0, currentFunctionId, null);
                // property
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                // PHP distinguishes subscript and member, but JavaScript does not
                // if (getCode(currentNode, sourceCode).search(/\[/) != -1) { // do not write like this
                if (currentNode.computed) { // use Esprima's parsing result
                    phptype = 'AST_DIM';
                    // distinguish if index is a literal (string or number), or value of a variable (identifier)
                    dfs(currentNode.property, nodeIdCounter, currentId, 1, currentFunctionId, null);
                } else {
                    phptype = 'AST_PROP';
                    // treat property name as a string
                    dfs(currentNode.property, nodeIdCounter, currentId, 1, currentFunctionId, {doNotUseVar: true});
                }
                nodes[currentId] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: phptype,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
            }
            break;
        case 'TemplateLiteral':
            if (outputStyle == 'c') {
                // quasis
                // Make a virtual node
                nodeIdCounter++;
                childNumberCounter++;
                vNodeId = nodeIdCounter;
                relsStream.push([currentId, vNodeId, parentOf].join(delimiter) + '\n');
                vNodeChildNumberCounter = 0;
                for (q of currentNode.quasis) {
                    nodeIdCounter++;
                    vNodeChildNumberCounter++;
                    relsStream.push([vNodeId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(q, nodeIdCounter, vNodeId, 0, currentFunctionId, null);
                }
                // Write the virtual node
                nodes[vNodeId] = {
                    label: 'AST_V',
                    type: 'TemplateLiteralQuasis',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                // expressions
                // Make a virtual node
                nodeIdCounter++;
                childNumberCounter++;
                vNodeId = nodeIdCounter;
                relsStream.push([currentId, vNodeId, parentOf].join(delimiter) + '\n');
                vNodeChildNumberCounter = 0;
                for (e of currentNode.expressions) {
                    nodeIdCounter++;
                    vNodeChildNumberCounter++;
                    relsStream.push([vNodeId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    dfs(e, nodeIdCounter, vNodeId, 0, currentFunctionId, null);
                }
                // Write the virtual node
                nodes[vNodeId] = {
                    label: 'AST_V',
                    type: 'TemplateLiteralExpressions',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
            } else if (outputStyle == 'php') {
                // // Warning: experimental support in PHP format.
                // // quasis
                // for (q of currentNode.quasis) {
                //     nodeIdCounter++;
                //     relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                //     dfs(q, nodeIdCounter, vNodeId, childNumberCounter, currentFunctionId, null);
                //     childNumberCounter++;
                // }
                // // expressions
                // for (e of currentNode.expressions) {
                //     nodeIdCounter++;
                //     relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                //     dfs(e, nodeIdCounter, vNodeId, childNumberCounter, currentFunctionId, null);
                //     childNumberCounter++;
                // }
                for (let i = 0; i < currentNode.quasis.length || i < currentNode.expressions.length; i++){
                    if (i < currentNode.quasis.length){
                        nodeIdCounter++;
                        relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                        dfs(currentNode.quasis[i], nodeIdCounter, vNodeId, childNumberCounter, currentFunctionId, null);
                        childNumberCounter++;
                    }
                    if (i < currentNode.expressions.length){
                        nodeIdCounter++;
                        relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                        dfs(currentNode.expressions[i], nodeIdCounter, vNodeId, childNumberCounter, currentFunctionId, null);
                        childNumberCounter++;
                    }
                }
            }
            // Finally, write the TemplateLiteral itself
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_ENCAPS_LIST',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'TemplateElement':
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'string',
                code: currentNode.value.raw,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'IfStatement':
            // test
            // Make a virtual node
            nodeIdCounter++;
            let testId = nodeIdCounter;
            relsStream.push([currentId, testId, parentOf].join(delimiter) + '\n');
            // go to test
            nodeIdCounter++;
            relsStream.push([testId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.test, nodeIdCounter, testId, 0, currentFunctionId, null);
            // Write the virtual node
            nodes[testId] = {
                label: 'AST_V',
                type: 'IfStatementTest',
                phptype: 'AST_IF_ELEM',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                childNum: 0,
                funcId: currentFunctionId
            };
            // consequent
            if (outputStyle == 'c') {
                // Make a virtual node
                nodeIdCounter++;
                let consequentId = nodeIdCounter;
                relsStream.push([currentId, consequentId, parentOf].join(delimiter) + '\n');
                // goto the consequent child node
                nodeIdCounter++;
                relsStream.push([consequentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.consequent, nodeIdCounter, consequentId, 0, currentFunctionId, null);
                // Write the virtual node
                nodes[consequentId] = {
                    label: 'AST_V',
                    type: 'IfStatementConsequent',
                    phptype: 'AST_STMT_LIST',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    childNum: 1,
                    funcId: currentFunctionId
                };
            } else if (outputStyle == 'php') {
                // If the child is not BlockStatement (AST_STMT_LIST in php), make the AST_STMT_LIST virtual node
                makeVirtualNodeForBody(currentNode.consequent, testId, 1, currentFunctionId, 'IfStatementConsequent');
            }
            // alternate (else)
            if (currentNode.alternate) {
                if (outputStyle == 'php') {
                    // Make the first virtual node
                    nodeIdCounter++;
                    let elseIfElemId = nodeIdCounter;
                    relsStream.push([currentId, elseIfElemId, parentOf].join(delimiter) + '\n');
                    // insert NULL node
                    nodeIdCounter++;
                    relsStream.push([elseIfElemId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                    nodes[nodeIdCounter] = {
                        label: 'AST_V',
                        type: 'NULL',
                        phptype: 'NULL',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        childNum: 0,
                        funcId: currentFunctionId
                    };
                    // If the child is not BlockStatement (AST_STMT_LIST in php), make the second virtual node
                    makeVirtualNodeForBody(currentNode.alternate, elseIfElemId, 1, currentFunctionId, 'IfStatementAlternate');
                    // Write the first virtual node
                    nodes[elseIfElemId] = {
                        label: 'AST_V',
                        type: 'IfStatementTest',
                        phptype: 'AST_IF_ELEM',
                        lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                        lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                        colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                        colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                        childNum: 1,
                        funcId: currentFunctionId
                    };
                }
            }
            // Write the virtual node
            nodes[testId] = {
                label: 'AST_V',
                type: 'IfStatementTest',
                phptype: 'AST_IF_ELEM',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                childNum: 0,
                funcId: currentFunctionId
            };
            // Finally, write the IfStatement itself
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_IF',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                // code: getCode(currentNode, sourceCode), // code would be too long
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'ThisExpression':
            if (outputStyle == 'php') {
                // make AST_VAR virtual node
                let vAstVarId = currentId;
                nodes[vAstVarId] = {
                    label: 'AST_V',
                    type: currentNode.type,
                    phptype: 'AST_VAR',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: childNum,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId
                };
                nodeIdCounter++;
                relsStream.push([vAstVarId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                // write the Identifier node
                nodes[nodeIdCounter] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'string',
                    name: 'this',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: getCode(currentNode, sourceCode),
                    funcId: currentFunctionId
                };
            }
            break;
        case 'ConditionalExpression':
            // test
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.test, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // consequent
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.consequent, nodeIdCounter, currentId, 1, currentFunctionId, null);
            // alternate
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.alternate, nodeIdCounter, currentId, 2, currentFunctionId, null);
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_CONDITIONAL',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'ContinueStatement':
        case 'BreakStatement':
            if (currentNode.type == 'ContinueStatement') phptype = 'AST_CONTINUE';
            else if (currentNode.type == 'BreakStatement') phptype = 'AST_BREAK';
            if (outputStyle == 'php') {
                // NULL node for depth (different in PHP & JS, currently no support)
                if (currentNode.label) console.log(`  Warning: uncompleted support for ${currentNode.type} with labels.`);
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    funcId: currentFunctionId
                };
            }
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: phptype,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'EmptyStatement':
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'NULL',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                childNum: childNum,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'TryStatement':
            // block
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.block, nodeIdCounter, currentId, 0, currentFunctionId, null);
            // handler
            // make a virtual AST_CATCH_LIST node
            nodeIdCounter++;
            let vAstCatchListId = nodeIdCounter;
            relsStream.push([currentId, vAstCatchListId, parentOf].join(delimiter) + '\n');
            // go to handler
            nodeIdCounter++;
            relsStream.push([vAstCatchListId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.handler, nodeIdCounter, vAstCatchListId, 0, currentFunctionId, null);
            // write the virtual AST_CATCH_LIST node
            nodes[vAstCatchListId] = {
                label: 'AST_V',
                type: 'TryStatementCatchList',
                phptype: 'AST_CATCH_LIST',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                childNum: 1,
                funcId: currentFunctionId
            };
            // finalizer
            if (currentNode.finalizer){
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                dfs(currentNode.finalizer, nodeIdCounter, currentId, 2, currentFunctionId, null);
            }
            // finally, write the TryStatement node
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_TRY',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'CatchClause':
            // make a virtual AST_NAME_LIST node
            let vAstNameListId = ++nodeIdCounter;
            relsStream.push([currentId, vAstNameListId, parentOf].join(delimiter) + '\n');
            nodes[vAstNameListId] = {
                label: 'AST_V',
                type: 'AstNameList',
                phptype: 'AST_NAME_LIST',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                childNum: 0,
                funcId: currentFunctionId
            };
            // make a virtual AST_NAME node
            let vAstNameId = ++nodeIdCounter;
            relsStream.push([vAstNameListId, vAstNameId, parentOf].join(delimiter) + '\n');
            nodes[vAstNameId] = {
                label: 'AST_V',
                type: 'AstName',
                phptype: 'AST_NAME',
                phpflag: 'NAME_NOT_FQ',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                childNum: 0,
                funcId: currentFunctionId
            };
            // make a virtual string node
            nodeIdCounter++;
            relsStream.push([vAstNameId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            nodes[nodeIdCounter] = {
                label: 'AST_V',
                type: 'Literal',
                phptype: 'string',
                code: 'Exception',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                childNum: 0,
                funcId: currentFunctionId
            };
            // param
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.param, nodeIdCounter, currentId, 1, currentFunctionId, null);
            // body
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            dfs(currentNode.body, nodeIdCounter, currentId, 2, currentFunctionId, null);
            // finally, write the CatchClause node
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_CATCH',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'ThrowStatement':
            nodeIdCounter++;
            relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
            if (currentNode.argument) {
                dfs(currentNode.argument, nodeIdCounter, currentId, 0, currentFunctionId, null);
            } else {
                // insert a NULL node
                nodes[nodeIdCounter] = {
                    label: 'AST_V',
                    type: 'NULL',
                    phptype: 'NULL',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    funcId: currentFunctionId
                };
            }
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                phptype: 'AST_THROW',
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                childNum: childNum,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                code: getCode(currentNode, sourceCode),
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
        case 'Super':
            if (outputStyle == 'php'){
                nodes[currentId] = {
                    label: 'AST',
                    phptype: 'AST_NAME',
                    phpflag: 'NAME_NOT_FQ',
                    childNum: childNum,
                    // code: currentNode.callee.name || getCode(currentNode.callee, sourceCode) || '',
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    funcId: currentFunctionId,
                    comment: comment,
                    loc: currentNode.loc
                };
                nodeIdCounter++;
                relsStream.push([currentId, nodeIdCounter, parentOf].join(delimiter) + '\n');
                nodes[nodeIdCounter] = {
                    label: 'AST',
                    type: currentNode.type,
                    phptype: 'string',
                    phpflag: (extra ? extra.flag : null) || null,
                    lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                    childNum: 0,
                    lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                    colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                    colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                    code: 'super',
                    funcId: currentFunctionId
                };
            }
            break;
        default:
            console.log(`  ${currentNode.type} goes default.`);
            nodes[currentId] = {
                label: 'AST',
                type: currentNode.type,
                lineLocStart: currentNode.loc ? currentNode.loc.start.line : null,
                lineLocEnd: currentNode.loc ? currentNode.loc.end.line : null,
                colLocStart: currentNode.loc ? currentNode.loc.start.column : null,
                colLocEnd: currentNode.loc ? currentNode.loc.end.column : null,
                childNum: childNum,
                funcId: currentFunctionId,
                comment: comment,
                loc: currentNode.loc
            };
            break;
    }
};

function makeVirtualNodeForBody(body, parentNode, childNum, currentFunctionId, ctype){
    if (!ctype){
        ctype = 'BlockStatement';
    }
    if (body.type != 'BlockStatement') {
        nodeIdCounter++;
        let vNodeId = nodeIdCounter;
        relsStream.push([parentNode, vNodeId, parentOf].join(delimiter) + '\n');
        nodeIdCounter++;
        relsStream.push([vNodeId, nodeIdCounter, parentOf].join(delimiter) + '\n');
        dfs(body, nodeIdCounter, vNodeId, 0, currentFunctionId, null);
        // Write the second virtual node
        nodes[vNodeId] = {
            label: 'AST_V',
            type: ctype,
            phptype: 'AST_STMT_LIST',
            lineLocStart: body.loc ? body.loc.start.line : null,
            lineLocEnd: body.loc ? body.loc.end.line : null,
            colLocStart: body.loc ? body.loc.start.column : null,
            colLocEnd: body.loc ? body.loc.end.column : null,
            childNum: childNum,
            funcId: currentFunctionId
        };
    } else { // If the child is BlockStatement
        nodeIdCounter++;
        relsStream.push([parentNode, nodeIdCounter, parentOf].join(delimiter) + '\n');
        dfs(body, nodeIdCounter, parentNode, childNum, currentFunctionId, null);
    }
}

function walkDir(dir, parentNodeId, callback) {
    /**
     * walk the dir and combine files together
     */
    let currentId = nodeIdCounter;
    if (outputStyle == 'php') {
        if (parentNodeId !== null) {
            relsStream.push([parentNodeId, currentId, 'DIRECTORY_OF'].join(delimiter) + '\n');
        }
        nodes[currentId] = {
            label: 'Filesystem',
            type: 'Directory',
            name: dir
        };
    } else if (outputStyle == 'c') {
        if (parentNodeId !== null) {
            relsStream.push([parentNodeId, currentId, 'IS_DIRECTORY_OF'].join(delimiter) + '\n');
        }
        nodes[currentId] = {
            label: 'Filesystem',
            type: 'Directory',
            name: dir
        };
    }
    nodeIdCounter++;
    fs.readdirSync(dir).forEach(f => {
        let dirPath = path.join(dir, f);
        let isDirectory = fs.statSync(dirPath).isDirectory();
        if (isDirectory) {
            walkDir(dirPath, currentId, callback);
        } else {
            if (f.endsWith(".js")) callback(path.join(dir, f), currentId);
        }
    });
};

function analyze(filePath, parentNodeId) {
    // read the file
    filename = filePath || 'stdin';
    if (analyzedModules.includes(filename)){
        console.log(("Skipping " + filename).white.inverse);
        return;
    }
    console.log(("Analyzing " + filename).green.inverse);
    if (filePath == null){
        // read from stdin
        filePath = 0;
    }
    sourceCode = fs.readFileSync(filePath, 'utf8');
    sourceCode = sourceCode.replace(/^#!.*\n/, '\n');
    sourceCode = sourceCode.replace(/\r\n/g, '\n');
    // initialize
    if (!program.expression){
        let currentId = nodeIdCounter;
        if (outputStyle == 'php') {
            if (parentNodeId !== null) {
                relsStream.push([parentNodeId, currentId, 'DIRECTORY_OF'].join(delimiter) + '\n');
            }
            nodes[currentId] = {
                label: 'Filesystem',
                type: 'File',
                name: filename
            };
        } else if (outputStyle == 'c') {
            if (parentNodeId !== null) {
                relsStream.push([parentNodeId, currentId, 'IS_DIRECTORY_OF'].join(delimiter) + '\n');
            }
            nodes[currentId] = {
                label: 'Filesystem',
                type: 'File',
                name: filename
            };
        }
        nodeIdCounter++;
    }
    // parse
    try {
        var root = esprima.parseModule(sourceCode, {
            loc: true,
            range: true,
            tolerant: true,
            attachComment: true
        });
        if (root.errors && root.errors.length > 0){
            console.log('Errors occurred when generating AST:'.lightRed.inverse);
            for (err of root.errors){
                console.log(err.toString().lightRed);
            }
        }
    } catch (e) {
        console.log(e);
    }
    if (!stdoutMode){
        console.dir(root);
    }
    // console.log(JSON.stringify(root, null, 2));
    let rootId = nodeIdCounter;
    if (program.expression){
        root = root.body[0].expression;
    }
    dfs(root, rootId, rootId - 1, 0, null, null);
    // output
    for (var i in nodes) {
        let u = nodes[i];
        let label = u.label;
        label = label == 'AST_V' ? 'AST' : u.label; // AST_V -> AST
        let childNum = u.childNum === 0 ? 0 : u.childNum || '';
        if (outputStyle == 'php') {
            // process and quote code
            // let code = u.operator || u.code || null;
            let quote = function(input, mode){
                let quoted = input || null;
                if (quoted === undefined || quoted === null) {
                    quoted = '';
                } else {
                    if (quoted.length > 1024){
                        quoted = quoted.substr(0, 1024);
                    }
                    switch(mode){
                        case 1:
                            quoted = quoted.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n|\r/g, '\\\\n').replace(/\t/g, '\\t');
                            break;
                        default:
                            quoted = quoted.replace(/\n|\r/g, '').replace(/\t/g, ' ').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
                            break;
                    }
                    quoted = '"' + quoted + '"';
                }
                return quoted;
            }
            let location = u.lineLocStart ? [u.lineLocStart, u.colLocStart || '', u.lineLocEnd || u.lineLocStart, u.colLocEnd || ''].join(':') : '';
            nodesStream.push([i, label, u.phptype || u.type, u.phpflag || '',
                u.lineLocStart !== null ? u.lineLocStart : '', quote(u.code), childNum, u.funcId || '',
                '', location, u.lineLocEnd !== null ? u.lineLocEnd : '', u.name || '', quote(u.comment, 1)
            ].join(delimiter) + '\n');
        } else if (outputStyle == 'c') {
            if (i == 0) continue;
            label = 'ANR';
            let location = u.lineLocStart ? [u.lineLocStart, u.colLocStart || 0, u.lineLocEnd || '', u.colLocEnd || 0].join(':') : '';
            let code = u.code || u.name || '';
            if (delimiter != ',') {
                code = code.replace(/\t|\n/g, '');
            }
            if (code.search(/\s|,|"/) != -1) {
                code = '"' + code.replace(/"/g, '\"\"') + '"';
            }
            nodesStream.push([label, i, u.ctype || u.type, code, location,
                u.funcId || '', childNum, '', u.operator || '', '', '', ''
            ].join(delimiter) + '\n');
        }
    }

    if (!program.expression){
        if (outputStyle == 'php') {
            relsStream.push([rootId - 1, rootId, 'FILE_OF'].join(delimiter) + '\n');
        } else if (outputStyle == 'c') {
            relsStream.push([rootId - 1, rootId, 'IS_FILE_OF'].join(delimiter) + '\n');
        }
    }

    nodeIdCounter++;
    nodes = []; // reset the node array but not the nodeIdCounter

    analyzedModules.push(filePath);
};

// main

if (program.search){
    if (program.search === true)
        program.search = '.';
    // search module in the specified path
    modulePath = searchModule(program.input, program.search)[0];
    if (modulePath && !requiredModules.has(modulePath)) {
        requiredModules.add(modulePath);
    }
} else {
    // analyze the designated source code files
    if (program.input === '-'){
        // analyze stdin
        analyze(null, null);
    } else {
        // analyze files
        if (!fs.statSync(dirname).isDirectory()) {
            analyze(dirname, null);
        } else {
            walkDir(dirname, null, analyze);
        }
    }
}

// analyze any required packages
for (let currentModule of requiredModules) {
    if (currentModule == 'built-in') continue;
    analyze(currentModule, null);
}

nodesStream.push(null);
relsStream.push(null);
