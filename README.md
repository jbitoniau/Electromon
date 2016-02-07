Electromon
==========

# Install
```Bash
# Create and activate python virtualenv
virtualenv .env
.env\Scripts\activate		# on Windows

# Install lib for accessing google spreadsheet
pip install gspread

# More install for authentication. Follow this guide:
# http://gspread.readthedocs.org/en/latest/oauth2.html
# and store json file locally here
pip install --upgrade oauth2client
pip install PyOpenSSL
```
