'use strict'

const path = require("path")
const process = require('process')

const levelup = require("levelup")
const leveldown = require("leveldown")

const promisify = require("./promisify")

class Db {
  constructor(options = {}) {
    this.data_path = options['data_path'] ||
      process.env.DATA_PATH ||
      '/data'
    this.collections = {}
  }

  getCollection(collectionName) {
    if (this.collections[collectionName]) {
      return this.collections[collectionName]
    }

    let coll_path = path.join(this.data_path, collectionName)
    let coll = levelup(leveldown(coll_path))

    this.collections[collectionName] = coll

    return coll
  }
}

module.exports = Db
