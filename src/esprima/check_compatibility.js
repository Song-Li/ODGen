#!/usr/bin/env node

const spawnSync = require('child_process').spawnSync;
const path = require('path');
const fs = require('fs');
const util = require('util');

var nodes = {};
var processed = 0, unsupported = 0, packageProcessed = 0;

var mainLogStream = fs.createWriteStream('check_compatibility_main.log');

function walkDir(dir, parentNodeId, callback) {
    fs.readdirSync(dir).forEach(f => {
        if (limit && packageProcessed >= limit) return;
        let dirPath = path.join(dir, f);
        let isDirectory = fs.statSync(dirPath).isDirectory();
        if (isDirectory) {
            var results = spawnSync('node', ['./main.js', dirPath]);
            (results.stdout + results.stderr).split('\n').forEach(data => {
                processOutput(f,data);
            });
        }
        packageProcessed++;
        console.log(`Finished analyzing ${f}. ${packageProcessed} packages finished in total. Here is report:`);
        for (let nodeName in nodes){
            console.log(`${nodeName.padEnd(30)} count: ${nodes[nodeName].count.toString().padStart(8)} isUnsupported: ${nodes[nodeName].unsupported.toString().padStart(5)}`);
        }
    });
    var statsLogStream = fs.createWriteStream('check_compatibility_stats.log');
    for (let nodeName in nodes){
        statsLogStream.write(`${nodeName.padEnd(30)} count: ${nodes[nodeName].count.toString().padStart(8)} isUnsupported: ${nodes[nodeName].unsupported.toString().padStart(5)}\n`);
        if (nodes[nodeName].unsupported){
            statsLogStream.write('  occurrence: ' + [...nodes[nodeName].occurrence] + '\n');
        }
    }
    mainLogStream.end();
    statsLogStream.end();
    console.log('All jobs finished.');
};

function processOutput(packageName, data){
    mainLogStream.write(data + '\n');
    if (data.match(/Current node: \d+ (\w+) \(.*\)/)){
        let nodeName = data.match(/Current node: \d+ (\w+) \(.*\)/)[1];
        // console.log(nodeName);
        processed++;
        if (!(nodeName in nodes)) nodes[nodeName] = {count: 0, unsupported: false, occurrence: new Set()};
        nodes[nodeName]['count']++;
    } else if (data.match(/Warning: uncompleted support for (\w+)\./)){
        let nodeName = data.match(/Warning: uncompleted support for (\w+)\./)[1];
        // console.log(nodeName);
        unsupported++;
        nodes[nodeName]['unsupported'] = true;
        nodes[nodeName]['occurrence'].add(packageName);
    } else if (data.match(/(\w+) goes default./)){
        let nodeName = data.match(/(\w+) goes default./)[1];
        // console.log(nodeName);
        unsupported++;
        nodes[nodeName]['unsupported'] = true;
        nodes[nodeName]['occurrence'].add(packageName);
    }
}

var dirname = process.argv[2];
var limit = process.argv[3] ? parseInt(process.argv[3]) : null;
walkDir(dirname);