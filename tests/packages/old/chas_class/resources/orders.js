'use strict'

const util = require('util')

const express = require("express")

const Logger = require("../logger")

const Order = require("../models/order")

let orders = express.Router()

let ROUTE_PREFIX = '/orders'

// 12345678-1234-1234-1234-123456789012
// d1589325-9fdf-49a2-a65a-eaeac8b569c4

const matcher_makers = {
  gteq: (key, value) => {
    let fn = (obj) => obj[key] >= value
    fn[util.inspect.custom] = () => `${key} gteq ${value}`
    return fn
  },
  lteq: (key, value) => {
    let fn = (obj) => obj[key] <= value
    fn[util.inspect.custom] = () =>`${key} lteq ${value}`
    return fn
  }
}

const always_match = (_obj) => true
always_match[util.inspect.custom] = () => 'always'

orders.get('/', (req, resp) => {
//  Logger.DEBUG(req.query)

  let filters = [always_match]

  if (req.query.filter) {
    for (const [masher, value] of Object.entries(req.query.filter)) {
      let [field, matcher] = masher.split(':')

      if ('' == value) continue

  //    Logger.DEBUG(`${field} ${matcher} => ${value}`)

      filters.push(matcher_makers[matcher](field, value))
    }
  }

  Logger.DEBUG(filters)

  Order.list().
    then(orders => {
      let matched_orders = orders.filter(order => {
        for (const filter of filters) {
          if (! filter(order)) {
            return false
          }
        }
        return true
      })

      resp.render('orders/index', {orders: matched_orders})
    }).
    catch(err => resp.render('error', {error: err}))
      })

orders.get(
  /^\/([0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12})$/,
  (req, resp) => {
    Order.load(req.params[0]).
      then(order => {
        let template = 'orders/show'
        if (order.pin == req.query.pin) template = 'orders/show_full'

        resp.render(template, {order: order})
      }).
      catch(err => {
        if (err.notFound) {
          resp.sendStatus(404)
          return
        }
        console.log(err)
        resp.sendStatus(400)
      })
        })

module.exports = orders
