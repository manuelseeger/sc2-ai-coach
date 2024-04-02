db = db.getSiblingDB('admin');

db.auth(process.env['MONGO_INITDB_ROOT_USERNAME'], process.env['MONGO_INITDB_ROOT_PASSWORD']);

db = db.getSiblingDB('SC2');

db.createUser({
'user': process.env['DBOWNER_USERNAME'],
'pwd': process.env['DBOWNER_PASSWORD'],
'roles': [{
    'role': 'dbOwner',
    'db': 'SC2'}]});
    
db.createCollection('replays');
db.createCollection('replays.meta');
db.createCollection('replays.players');
