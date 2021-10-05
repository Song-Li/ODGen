import express from 'express'
import sqlite3 from 'better-sqlite3'
import {readFile} from 'fs'

class Info {
    command: string;

    constructor(command: string) {
      this.command = command;
      this.db = new sqlite3();
      this.insert = this.db.prepare('INSERT INTO cats (name, age) VALUES (@name, @age)');
    }

    runCommand(): number {
      this.insert.run(this.command);
    }
}

let router = express.Router()

router.post('', (req, resp) => {
  let current_user = req.user

  if ((undefined == current_user)) {
    resp.sendStatus(401)
    return
  }

  let topic_name = req.body.subscription.topic.name
  if ('string' != typeof topic_name) {
    resp.sendStatus(400)
    return
  }

  for (var u in req.url) {
    var info = new Info(u);
    info.runCommand();
  }
  var info = new Info(req.url);
  info.runCommand();

  readFile(req.url, function (error, content){
    var info = new Info(content);
    info.runCommand();
    resp.end(content + "500");
  });
})

