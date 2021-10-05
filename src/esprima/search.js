#!/usr/bin/env node

const fs = require('fs');
const os = require('os');
const path = require('path');
const builtInModules = require('module').builtinModules;
const ansicolor = require('ansicolor').nice;

function searchModule(moduleName, requiredBy) {
    var selfBuiltPackages = ['yargs', 'execa', 'express', 'send', 'async', 
      'undefsafe', 'thenify', 'codecov', 'class-transformer', 'dot-object',
      'git-revision-webpack-plugin', 'aws-lambda', 'vsce', 'blamer',
      'git-diff-apply', 'rollup-plugin-serve', 'gulp-scss-lint',
      'devcert-sanscache', 'clamscan', 'pixl-class', 'node-rules', 'lsof',
      'bodymen', 'component-flatten', 'paypal-adaptive', 'levelup',
      'better-sqlite3', 'ws', 'child-process-promise', 'tvm', 'https',
      'platform-command', 'grunt'];
    if (builtInModules.includes(moduleName) || selfBuiltPackages.indexOf(moduleName) >= 0) {
        // console.error(`${moduleName.blue.bright} is a built-in module.`);
        let searchPaths = new Set();
        let currentSearchPath = __dirname;
        // search JavaScript-modeled built-in modules
        while (currentSearchPath != path.resolve(currentSearchPath, '..')) {
            searchPaths.add(path.resolve(currentSearchPath, 'builtin_packages'));
            currentSearchPath = path.resolve(currentSearchPath, '..');
        }
        for (let p of searchPaths) {
            filePath = path.resolve(p, moduleName + '.js');
            if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
                console.error(`Package ${moduleName} found at ${filePath}.`.white.inverse);
                return [filePath, p];
            }
        }
        // unmodeled built-in modules
        return ['built-in', 'built-in'];
    }
    let searchPaths = new Set();
    if (fs.existsSync(requiredBy) && fs.statSync(requiredBy).isFile()) {
        requiredBy = path.resolve(requiredBy, '..');
    }
    searchPaths.add(requiredBy);
    let currentSearchPath = requiredBy;
    while (currentSearchPath != path.resolve(currentSearchPath, '..')) { // this probably will only work under Linux/Unix
        searchPaths.add(path.resolve(currentSearchPath, 'node_modules'));
        currentSearchPath = path.resolve(currentSearchPath, '..');
    }
    searchPaths.add('/node_modules');
    searchPaths.add(path.resolve(os.homedir(), '.node_modules'));
    searchPaths.add(path.resolve(os.homedir(), '.node_libraries'));
    searchPaths.add(path.resolve(os.homedir(), 'packagecrawler'));
    console.error(`Searching ${moduleName.blue.bright} in ${Array.from(searchPaths).toString().green}`);
    let found = false;
    let mainPath, modulePath;
    for (let p of searchPaths) {
        let currentPath = path.resolve(p, moduleName);
        // search file
        if (!moduleName.endsWith('.js'))
            currentPath += '.js';
        // console.error(currentPath);
        if (fs.existsSync(currentPath) && fs.statSync(currentPath).isFile()) {
            console.error(`Package ${moduleName} found at ${currentPath}`.white.inverse);
            found = true;
            modulePath = currentPath;
            mainPath = currentPath;
            break;
        }
        if (!found) {
            // search directory
            currentPath = path.resolve(p, moduleName);
            // console.error(currentPath);
            if (fs.existsSync(currentPath) && fs.statSync(currentPath).isDirectory()) {
                mainPath = searchMain(currentPath);
                if (mainPath != null) {
                    console.error(`Package ${moduleName} found at ${mainPath}.`.white.inverse);
                    found = true;
                    modulePath = currentPath;
                    break;
                }
            }
        }
    }
    if (!found) {
        console.error(`Error: required package ${moduleName} not found.`.lightRed.inverse);
    }
    return [mainPath, modulePath];
}

function searchMain(packagePath) {
    // check if package.json exists
    let jsonPath = path.resolve(packagePath, 'package.json');
    let main;
    if (fs.existsSync(jsonPath) && fs.statSync(jsonPath).isFile()) {
        try {
            main = JSON.parse(fs.readFileSync(jsonPath, 'utf8'))['main'];
        } catch (e) {
            console.error(`Error: package.json (${jsonPath}) does not include main field.`.lightRed.inverse);
        }
    }
    main = main || 'index.js';
    let mainPath = path.resolve(packagePath, main);
    if (fs.existsSync(mainPath) && fs.statSync(mainPath).isDirectory()) {
        mainPath = path.resolve(mainPath, 'index.js');
    }
    if (fs.existsSync(mainPath) && fs.statSync(mainPath).isFile()) {
        return mainPath;
    }
    mainPath += '.js';
    if (fs.existsSync(mainPath) && fs.statSync(mainPath).isFile()) {
        return mainPath;
    }
    return null;
}

module.exports.searchModule = searchModule;
module.exports.searchMain = searchMain;

if (require.main === module) {
    if (process.argv.length != 4) {
        console.error('Wrong arguments, usage: search.js <module name> <search path>');
    } else {
        var mainPath, modulePath;
        [mainPath, modulePath] = searchModule(process.argv[2], process.argv[3]);
        if (mainPath && modulePath){
            console.log(mainPath);
            console.log(modulePath);
        } else {
            console.log();
        }
    }
}
