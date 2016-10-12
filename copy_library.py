import requests
import math
import sys
import os
import json
import yaml

requests.packages.urllib3.disable_warnings()

# Helper functions
def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i + n]

def get_config():
    try:
        config = yaml.load(open('config.yml'))
    except IOError:
        sys.stderr.write('Unable to open configuration file "config.yml"\n')
        sys.exit()
    except Exception, e:
        sys.stderr.write('Something went wrong reading the configuratio file (%s)\n'%str(e))
        sys.exit()
    if 'api_url' not in config:
        config['api_url'] = 'https://api.adsabs.harvard.edu/v1/biblib'
    return config

def get_library(config):
    # Retrieve the contents of the library specified
    # rows: the number of records to retrieve per call
    rows = 25
    start = 0
    params = {'start': start, 'rows': rows, 'fl': 'bibcode'}
    # Define the header information to be used in all calls
    headers = {
        'Authorization': 'Bearer:{}'.format(config['api_token']),
        'Content-Type': 'application/json',
    }
    # Get first batch of documents and the actual number of documents in the library
    r = requests.get('{}/libraries/{id}'.format(config['api_url'],id=config['library_id']),
        headers=headers,
        params=params
    )
    # If no library name was specified in the config, we will use the name of the actual library
    if 'library_name' not in config:
        config['library_name'] = r.json()['metadata']['name']
    # Store the library description, which will be copied over to the target library
    config['description'] = r.json()['metadata']['description']
    # From the information returned, determine how many records there are in the library
    num_documents = r.json()['metadata']['num_documents']
    # Store the bibcodes of this first batch
    documents = r.json()['documents']
    # Given the number of rows to be retrieved per call, how often do we need to paginate to get
    # all records from the library?
    num_paginates = int(math.ceil((num_documents) / (1.0*rows)))
    # Update the start position with the number of records we have retrieved so far
    start += rows
    # Start retrieving the remainder of the contents
    for i in range(num_paginates):
        # Update the 'start' attribute of the query parameters
        params['start'] = start
        # Fire off the
        r = requests.get('{}/libraries/{id}'.format(config['api_url'],id=config['library_id']),
            headers=headers,
            params=params
        )
        # If we don't get a HTTP status code back of 200, something went wrong
        if r.status_code != requests.codes.ok:
                    # hopefully if something went wrong you'll get a json error message
                    e = simplejson.loads(r.text)
                    sys.stderr.write("error retrieving results for library %s: %s\n" % (config['library_id'], e['error']))
                    return {'error':'something went wrong! (%s)' % e['error']}
        # Get all the documents that are inside the library
        try:
            data = r.json()['documents']
        except ValueError:
            raise ValueError(r.text)
        # Add the bibcodes from this batch to the collection
        documents.extend(data)
        # Update the start position for the next batch
        start += rows

    return documents

def create_new_library(records, config):
    # To record what was done
    log = []
    nrecs = 0
    # Since we there is a limit to the amount of bibcodes that can be submitted in one request,
    # the list of bibcodes is split up into batches
    biblists = list(chunks(records, 500))
    # Define the header information to be used in all calls
    headers = {
        'Authorization': 'Bearer:{}'.format(config['api_token']),
        'Content-Type': 'application/json',
    }
    # First check if the target library already exists
    # 1. Get the info for all libraries owned by the current user
    r = requests.get(
        '{}/libraries'.format(
            config['api_url']
        ),
        headers=headers
    )
    # 2. Given the library name that we have, see if there is an entry for it. 
    #    If yes, get the library identifier for it.
    try:
        libdata = r.json()['libraries']
        libid = [e['id'] for e in libdata if e['name'] == config.get('library_name', 'NA')][0]
    except:
        libdata = []
        libid   = None
    # If we have a library identifier, we have an existing library and it needs to be updated.
    # Otherwise, a new library needs to be created using the first batch, and if there are any
    # more batches, the newly created library needs to be updated with these remaining batches
    if not libid:
        # We are creating a new library with the first entry in biblists
        # Pop the first batch from the list with batches
        biblist = biblists.pop(0)
        # Compile the necessary information to create the new library
        payload = {'name': config['library_name'], 
                   'description': config['description'], 
                   'public': False,
                   'bibcode': biblist
                }
        # Create the new library
        r = requests.post(
            '{}/libraries'.format(
                config['api_url']
            ),
            headers=headers,
            data=json.dumps(payload)
        )
        # The response should contain the identifier for the new library
        try:
            libid = r.json()['id']
        except:
            pass
        log.append('Created a new library (name: %s, description: %s, ID: %s)' % (config['library_name'], config['description'], libid))
        nrecs += len(biblist)
    # Process the case where there is a library ID and bibcodes to process
    if libid and len(biblists) > 0:
        # We have an existing library and bibcodes to be added
        for biblist in biblists:
            payload = {'bibcode': biblist, 'action': 'add'}
            r = requests.post(
                        '{}/documents/{id}'.format(
                            config['api_url'],
                            id=libid
                        ),
                        headers=headers,
                        data=json.dumps(payload)
                    )
            try:
                nrecs += r.json()['number_added']
            except:
                pass
    log.append('Number of records added to the library: %s' % nrecs)
    return log
    
if __name__ == '__main__':
    # First get the config parameters to do the work    
    config = get_config()
    # Retrieve the list of bibcodes to be copied over
    recs = get_library(config)
    if 'error' in bibcodes:
        print recs
    # Populate the target library with the bibcodes
    res      = create_new_library(recs, config)
    # What did we do?
    print "\n".join(res)
    
