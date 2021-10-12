'use strict'

const fs = require('fs')
const path = require('path')
const process = require('process')

const sprintf = require('sprintf-js').sprintf

const Db = require("../db")
const Logger = require("../logger")

const extend = require("../extend").mutable

let collection = new Db().getCollection("tweets")

const PHOTO_DIR = process.env.PHOTO_DIR || '/data/photos'
fs.mkdirSync(PHOTO_DIR, {recursive: true})

// reformat ids before 5138 CE
//            01601922097303
const MAX_NOW = 99999999999999
const MIN_NOW = 0

const ID_FMT = "%014d-%06d"
const MIN_ID = sprintf(ID_FMT, 0, 0)

function mk_id() {
  let now = new Date().valueOf()
  let inv_now = MAX_NOW - now

  return sprintf(ID_FMT,
                     inv_now,
                 Math.floor(Math.random() * 1000000))
}


class Tweet {
  constructor(options) {
    if ('string' == typeof options) {
      options = JSON.parse(options)
    }
    else if (Buffer.isBuffer(options)) {
      options = JSON.parse(options.toString())
    }

    extend(this, options)
  }

  value() {
    var running = {id: this.id,
                   body: this.body,
                   created_at: this.created_at}
    if (this.mime_type) {
      running.mime_type = this.mime_type
    } else if (this.uploaded_photo) {
      running.mime_type = this.uploaded_photo.mimetype
    }

    return JSON.stringify(running)
  }

  createdAt() {
    if (undefined != this._createdAt) return this._createdAt

    return this._createdAt = new Date(this.created_at)
  }

  afterCreate(resolve, reject) {
    Logger.DEBUG(`doing afterCreate with ${this.uploaded_photo}`)
    if (this.uploaded_photo) {
      fs.copyFile(this.uploaded_photo.path,
                  this.photoPath(),
                  fs.constants.COPYFILE_FICLONE,
                  (err) => {
                    if (err) return reject(err)
                    return resolve(this)
                  }
                 )
      return
    }

    Logger.DEBUG("did afterCreate with no photo")

    resolve(this)
  }

  photoPath() {
    return path.join(PHOTO_DIR, this.id)
  }

  static create(options) {
    let id = mk_id()
    let nuevo = new Tweet(extend(options, {id: id,
                                           created_at: Date.now()}))

    let db_px = collection.put(id, nuevo.value())

    let creat_px = new Promise((resolve, reject) => {
      db_px.
        catch(err => reject(err)).
        then(() => nuevo.afterCreate(resolve, reject))
    })

    return creat_px
  }

  static list(before = MIN_ID, limit = 25) {
    let rs = collection.createValueStream({gt: before, limit: limit})

    let got_tweets = []

    let list_px = new Promise((resolve, reject) => {
      rs.on('error', err => reject(err))
      rs.on('data', data => got_tweets.push(new Tweet(data)))

      let did_already_close = false
      let maybe_resolve = () => {
        if (did_already_close) return;

        did_already_close = true
        resolve(got_tweets)
      }
      rs.on('close', maybe_resolve)
      rs.on('end', maybe_resolve)
    })

    return list_px
  }

  static load(id) {
    let get_px = collection.get(id)
    let load_px = new Promise((resolve, reject) => {
      get_px.
        catch(err => reject(err)).
        then(data => {
          try {
            resolve(new Tweet(data.toString()))
          } catch (err) {
            reject(err)
          }
        })
    })

    return load_px
  }
}

module.exports = Tweet
