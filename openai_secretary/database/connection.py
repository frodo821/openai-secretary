from os.path import expanduser, dirname, exists, abspath, join
from os import makedirs
from sqlite3 import Connection
from pony import orm

db = orm.Database()
db_path = expanduser('~/.oai_secretary/master.db')
ext_path = abspath(join(dirname(__file__), '..', 'plugins', 'vector_cosine_similarity'))

if not exists(db_dir := dirname(db_path)):
  makedirs(db_dir)

db.bind(provider='sqlite', filename=db_path, create_db=True)


@db.on_connect('sqlite')
def init_connection(db, connection: Connection):
  connection.enable_load_extension(True)
  connection.load_extension(ext_path)
  connection.enable_load_extension(False)
