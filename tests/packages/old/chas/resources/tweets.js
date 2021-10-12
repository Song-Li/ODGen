'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

const express = require("express");

const multer = require("multer");

const Logger = require("../logger");

const Tweet = require("../models/tweet");

let tweets = express.Router();
let ROUTE_PREFIX = '/tweets';
let upload = multer({
  storage: multer.diskStorage({})
});
tweets.get('/', (req, resp) => {
  Tweet.list().then(tweets => {
    resp.render('tweets/index', {
      tweets: tweets
    });
  }).catch(err => resp.render('error', {
    error: err
  }));
});
tweets.get(/^\/page\/([^\/]+)$/, (req, resp) => {
  Tweet.list(req.params[0]).then(tweets => {
    resp.render('tweets/index', {
      tweets: tweets
    });
  }).catch(err => resp.render('error', {
    error: err
  }));
});
tweets.post('/', upload.single('tweet[photo]'), (req, resp) => {
  Logger.DEBUG(JSON.stringify(req.body));
  let tweet_attrs = {
    body: req.body.tweet.body
  };

  if (req.file) {
    tweet_attrs.uploaded_photo = req.file;
  }

  Logger.DEBUG(JSON.stringify(tweet_attrs));
  Tweet.create(tweet_attrs).then(tweet => {
    resp.redirect(`${ROUTE_PREFIX}/${tweet.id}`);
  }).catch(err => resp.render('error', {
    error: err
  }));
});
tweets.get(/^\/([^\/]+)$/, (req, resp) => {
  Tweet.load(req.params[0]).then(tweet => resp.render('tweets/show', {
    tweet: tweet
  })).catch(err => resp.sendStatus(400));
});
tweets.get(/^\/([^\/]+)\/photo$/, (req, resp) => {
  Logger.DEBUG(req.params[0]);
  let tweet = new Tweet({
    id: req.params[0]
  });
  return resp.sendFile(tweet.photoPath());
});
module.exports = tweets;