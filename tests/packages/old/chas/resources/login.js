'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

const crypto = require("crypto");

const fs = require('fs');

const cookieSession = require("cookie-session");

const express = require("express");

const Logger = require("../logger");

const User = require('../models/user');

var token;

try {
  token = fs.readFileSync('/token');
} catch (e) {
  Logger.ERROR(`got ${e} trying to read /token`);
  token = '__beacon_placeholder_token__';
}

let login = express.Router();
login.use(cookieSession({
  name: 'beacon_ogin_session',
  keys: [crypto.randomBytes(64).toString()],
  maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days

}));
let ROUTE_PREFIX = '/login';

function current_user(req, resp) {
  if (resp.locals.user) return Promise.resolve(resp.locals.user);

  if (req.session.username) {
    let user_px = User.load(req.session.username).then(user => {
      resp.locals.user = user;
      return user;
    });
    return user_px;
  }

  return Promise.resolve(null);
}

login.get('/', (req, resp) => {
  current_user(req, resp).then(user => {
    if (null != user) {
      return resp.redirect('/login/did_login');
    }

    return resp.render('login/index');
  });
});
login.post('/logout', (req, resp) => {
  req.session = null;
  resp.redirect('/login');
});
login.post('/', express.urlencoded({
  extended: true
}), (req, resp) => {
  var candidate_user;
  current_user(req, resp).then(maybe_user => {
    if (null != maybe_user) {
      resp.locals.did_render = true;
      resp.redirect('/login/did_login');
      return Promise.reject('already logged in');
    }

    Logger.DEBUG(`loading user ${req.body.user.username}`);
    return User.load(req.body.user.username);
  }).then(user => {
    if (null == user) {
      let msg = `got null user for username ${req.body.user.username}`;
      return Promise.reject(msg);
    }

    candidate_user = user;
    Logger.DEBUG(`authenticating`);
    return user.authenticate(req.body.user.password);
  }).then(scrypt_result => {
    if (!scrypt_result) {
      resp.locals.did_render = true;
      resp.render('login/index');
      return Promise.reject('failed password check');
    }

    Logger.DEBUG(`did authenticate user`);
    resp.locals.user = candidate_user;
    req.session.username = candidate_user.name;
    return resp.redirect('/login/did_login');
  }).catch(reason => {
    Logger.ERROR(reason);
    if (!resp.locals.did_render) resp.render('login/index');
  });
});
login.post('/new', express.urlencoded({
  extended: true
}), (req, resp) => {
  current_user(req, resp).then(maybe_user => {
    if (null != maybe_user) return Promise.reject(null);
    Logger.INFO(`not currently logged in, checking ${req.body.user.name}`);
    return User.maybe_load(req.body.user.name);
  }).then(existing_user => {
    if (null != existing_user) return Promise.reject(null);
    Logger.INFO(`not clobbering a user..., creating ${req.body.user}`);
    return User.create(req.body.user);
  }).then(new_user => {
    Logger.INFO('did create user...');
    req.session.username = new_user.name;
    resp.redirect('/login/did_login');
  }).catch(reason => {
    Logger.ERROR(reason);
    resp.render('login/index');
  });
});
login.get('/did_login', (req, resp) => {
  current_user(req, resp).then(maybe_user => {
    Logger.DEBUG(`session user ${maybe_user.name}`);
    if (null == maybe_user) return Promise.reject(null);
    if (maybe_user.is_admin) return resp.render('login/admin', {
      token: token
    });
    return resp.render('login/did_login');
  }).catch(_reason => resp.redirect('/login/'));
});
module.exports = login;