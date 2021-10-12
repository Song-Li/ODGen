'use strict'

const fs = require('fs')
const net = require("net")
const process = require("process")

const express = require("express")

const Logger = require("./logger")

function mount(app, file, path) {
    let sub_router = require(`./resources/${file}.js`)
    app.use(path, sub_router)
}

function main(_argv) {
  if (! process.env.CHESS) {
    Logger.FATAL("This application is for research purposes only")
    process.exit(1)
  }

  if (! process.env.DONT_DELETE_CHEATSHEET) {
    fs.rmdirSync('/data/users_cheatsheet', {recursive: true})
  }

  let app = express()

  app.set('view engine', 'pug')
  app.set('views',
          process.env.VIEW_DIR || '/static/view')

  app.use('/static',
          express.static(process.env.STATIC_DIR || '/static/static'))

  mount(app, 'tweets', '/tweets/')
  mount(app, 'orders', '/orders/')
  mount(app, 'login', '/login/')
  mount(app, 'index', '/')

  let port = parseInt(process.env.PORT || 3028)
  app.listen(port, () => {
    Logger.INFO(`beacon listening on port ${port}`)
  })

}

main(process.argv)
