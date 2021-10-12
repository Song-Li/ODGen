'use strict'

const express = require("express")

const Logger = require("../logger")

let index = express.Router()

index.get('/', (req, resp) => {
    resp.render('index')
})

index.get('/query-parsing', (req, resp) => {
    resp.render('console', {data: JSON.stringify(req.query)})
})

module.exports = index
