'use strict';

function objectAssign(target, properties) {
  for (var key in properties) {
    target[key] = properties[key];
  }
}

const crypto = require('crypto');

const Db = require("../db");

const Logger = require("../logger");

const extend = require("../extend").mutable;

let collection = new Db().getCollection("users");

function User(options) {
  if ('string' == typeof options) {
    options = JSON.parse(options);
  } else if (Buffer.isBuffer(options)) {
    options = JSON.parse(options.toString());
  }

  extend(this, options);
}

objectAssign(User.prototype, {
  authenticate: function authenticate(candidate_password) {
    let expected_digest = Buffer.from(this.password_digest, 'base64');
    let scrypt_px = new Promise((resolve, reject) => {
      crypto.scrypt(candidate_password, Buffer.from(this.password_salt, 'base64'), 64, (err, got_digest) => {
        if (err) reject(err);
        resolve(crypto.timingSafeEqual(expected_digest, got_digest));
      });
    });
    return scrypt_px;
  },
  beforeCreate: function beforeCreate() {
    this.password_salt = crypto.randomBytes(32);
    this.password_digest = crypto.scryptSync(Buffer.from(this.password), this.password_salt, 64);
  },
  value: function value() {
    return JSON.stringify({
      name: this.name,
      password_salt: this.password_salt,
      password_digest: this.password_digest,
      is_admin: this.is_admin
    });
  }
});
objectAssign(User, {
  create: function create(options) {
    let nuevo = new User(options);
    nuevo.beforeCreate();
    let db_px = collection.put(options.name, nuevo.value());
    let creat_px = new Promise((resolve, reject) => {
      db_px.catch(err => reject(err)).then(() => resolve(nuevo));
    });
    return creat_px;
  },
  load: function load(id) {
    let get_px = collection.get(id);
    let load_px = new Promise((resolve, reject) => {
      get_px.catch(err => reject(err)).then(data => {
        try {
          resolve(new User(data.toString()));
        } catch (err) {
          reject(err);
        }
      });
    });
    return load_px;
  },
  maybe_load: function maybe_load(id) {
    Logger.INFO(`getting ${id}`);
    let get_px = collection.get(id);
    let load_px = new Promise((resolve, reject) => {
      get_px.then(data => {
        Logger.DEBUG(data);

        try {
          resolve(new User(data.toString()));
        } catch (err) {
          Logger.DEBUG(err);
          reject(err);
        }
      }).catch(err => {
        Logger.DEBUG(err);
        if (err.notFound) resolve(null);else reject(err);
      });
    });
    return load_px;
  }
});
module.exports = User;