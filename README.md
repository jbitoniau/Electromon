Electromon
==========

# Install
```Bash
# Create and activate python virtualenv
sudo pip install virtualenv
virtualenv .env
source .env/bin/activate		# on Windows .env\Scripts\activate

# Install lib for accessing google spreadsheet
pip install gspread

# More install for authentication. Follow this guide:
# http://gspread.readthedocs.org/en/latest/oauth2.html
# and store json file locally here
pip install --upgrade oauth2client

# PyOpenSSL need to C compile stuff (on the pi) 
# so python dev headers/libs are required
sudo apt-get install python2.7-dev
sudo apt-get install libffi-dev
sudo apt-get install libssl-dev
pip install PyOpenSSL
```
