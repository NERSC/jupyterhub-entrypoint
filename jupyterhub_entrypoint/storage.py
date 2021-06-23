#########################################################################
# @author Josh Geden
# Implementation of a CRUD storage system
# Manages the storage of entrypoints using one json file per entrypoint
#########################################################################

import os
import json
import uuid
from pathlib import Path


class Storage:
    """Interface for a CRUD database"""
    async def create(self, user):
        raise NotImplementedError

    async def read(self, user):
        raise NotImplementedError

    async def update(self, user):
        raise NotImplementedError

    async def delete(self, user):
        raise NotImplementedError


class FileStorage(Storage):
    """
    Implements CRUD database interface by using json files to store info

    Doctest example
    >>> storage = FileStorage(template='./test_data/{user[0]}/{user}/{type}/{uuid}.json')

    >>> storage.create('test_user', 'Test Script', '/path/to/script.sh', 'test_entrypoint', ['test_system'], '999')
    True

    >>> storage.read('test_user', 'test_entrypoint', 'test_system')
    {'test_user': [{'name': 'Test Script', 'entrypoint': '/path/to/script.sh', 'type': 'test_entrypoint', 'systems': ['test_system'], 'id': '999'}]}

    >>> storage.read('test_user', 'test_system', 'test_system')
    Traceback (most recent call last):
    ... 
    FileNotFoundError: [Errno 2] No such file or directory: ...'

    >>> storage.update('test_user', 'Test Script', '/path/to/script.sh', '999', 'test_entrypoint', 'test_system')
    True

    >>> storage.read('test_user', 'test_system', 'test_system')
    {'test_user': [{'name': 'Test Script', 'entrypoint': '/path/to/script.sh', 'type': 'test_entrypoint', 'systems': ['test_system'], 'id': '999'}]}

    >>> storage.delete('test_user', 'test_system', 'current')
    True

    >>> storage.delete('test_user', 'test_entrypoint', '999')
    True

    Clean up test files created
    >>> os.rmdir('./test_data/t/test_user/test_entrypoint')
    >>> os.rmdir('./test_data/t/test_user/test_system')
    >>> os.rmdir('./test_data/t/test_user')
    >>> os.rmdir('./test_data/t')
    >>> os.rmdir('./test_data')
    """

    # define the default path template if not set when object is created
    def __init__(self, template='./data/{user[0]}/{user}/{type}/{uuid}.json'):
        self.template = template

    # return the parent directory for a certain file type
    def dir_path(self, user, type):
        uuid = 0  # we're interested in getting the parent folder, so uuid can be anything
        return Path(self.template.format(user=user, type=type, uuid=uuid)).parent

    # return the file path for a new json file
    def doc_path(self, user, type, default_id=0):
        id = str(uuid.uuid4())
        if default_id != 0:
            id = default_id
        return Path(self.template.format(user=user, type=type, uuid=id)), id

    # record a new entrypoint by creating a new json file for it
    # returns True if a new file is created successfully, otherwise returns False
    def create(self, user, name, path, entrypoint_type, systems, default_id=0):
        # create a path for new entrypoint as /{user}/{type}/{uuid}.json, hold on to the generated id
        doc_path, id = self.doc_path(user, entrypoint_type, default_id)
        print(f'Creating new file: {doc_path}')

        # default_id can be overwritten to provide a custom file name in the form {entrypoint_type}/{default_id}.json
        if default_id != 0:
            id = default_id

        # create the parent directories for the file if they don't exist
        doc_path.parent.mkdir(parents=True, exist_ok=True)

        # attempt to write the information to the doc path
        try:
            with open(doc_path, 'w') as f:
                dat = {"name": name, "entrypoint": path,
                       "type": entrypoint_type, "systems": systems, "id": id}
                json.dump(dat, f)
            return True
        except Exception as e:
            print('Error: ' + str(e))
        return False

    # reads all the files in a type folder for a given system (e.g. all conda files marked for 'cori')
    # returns an array of the read entrypoint information, or None if the array is empty
    def read(self, user, type, system):
        # get the directory for the type to be read
        dir_path = self.dir_path(user, type)

        # attempt to read all files in a type directory
        res = []
        for filename in os.listdir(dir_path):
            try:
                if '.json' in filename:
                    with open(os.path.join(dir_path, filename), 'r') as f:
                        dat = json.loads(f.read())
                        # only keep the data if it is marked for the selected system
                        if system in dat['systems']:
                            res.append(dat)
            except Exception as e:
                print(
                    f'Error trying to read: {filename} ({type}, {system}): {str(e)}')

        if res != []:
            return {user: res}
        return None

    # change the current selected entrypoint for a certain system
    # returns True if the '{system}/current.json' is created/updated, False otherwise
    def update(self, user, name, path, entrypoint_id, entrypoint_type, system):
        print(f'Updating with: {entrypoint_type}/{entrypoint_id}.json')

        # create the directory path for the system
        out_dir = self.dir_path(user, system)
        out_dir.parent.mkdir(parents=True, exist_ok=True)

        # create the '{system}/current.json' file to write to
        outfile = Path(os.path.join(out_dir, 'current.json'))
        outfile.parent.mkdir(parents=True, exist_ok=True)

        print(f'Writing to {outfile}')
        # attempt to write to the '{system}/current.json' file to update the selected entrypoint
        try:
            with open(outfile, 'w') as f:
                dat = {"name": name, "entrypoint": path,
                       "type": entrypoint_type, "systems": [system], "id": entrypoint_id}
                json.dump(dat, f)
            return True
        except Exception as e:
            print(f'Update Error: {e}')

        return False

    # delete a json file by type and id
    # returns True if a file is deleted, False otherwise
    def delete(self, user, type, id):
        dir_path = self.dir_path(user, type)
        doc_path = Path(os.path.join(dir_path), f'{id}.json')

        try:
            doc_path.unlink()
            return True
        except:
            return False


if __name__ == '__main__':
    import doctest
    # disable print so it doesn't conflict with doctest
    print = lambda *args, **kwargs: None
    doctest.testmod(optionflags=doctest.ELLIPSIS)
