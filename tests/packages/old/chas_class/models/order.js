'use strict'

const Db = require("../db")
const Logger = require("../logger")

const extend = require("../extend").mutable

let collection = new Db().getCollection("orders")

class Order {
  constructor(options) {
    if ('string' == typeof options) {
      options = JSON.parse(options)
    }
    else if (Buffer.isBuffer(options)) {
      options = JSON.parse(options.toString())
    }

    extend(this, options)
  }

  static list(limit = 25) {
    let rs = collection.createValueStream({limit: limit})

    let got_orders = []

    let list_px = new Promise((resolve, reject) => {
      rs.on('error', err => reject(err))
      rs.on('data', data => got_orders.push(new Order(data)))

      let did_already_close = false
      let maybe_resolve = () => {
        if (did_already_close) return;

        did_already_close = true
        resolve(got_orders)
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
            resolve(new Order(data.toString()))
          } catch (err) {
            reject(err)
          }
        })
    })

    return load_px
  }
}

module.exports = Order
