In order to run the script, we advise to install a virtual environment with Python 2.7

  virtualenv --no-site-packages -ppython2.7 venv
   
which will install the virtual environment in the sub-directory 'venv'. Start the virtual
environment with

  source venv/bin/activate
  
update pip with

  pip install -U pip
  
and install the required modules

  pip install -r requirements.txt

Next, add the necessary information to the configuration file ("config.yml"). The only
required information is

1. The library ID of the library to be copied
2. The API key of the user who will receive the library

Note: in order to this script to work, the library in question has to be made public.

Execute the script:

  python copy_library.py