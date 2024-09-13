Simple tool for range diffing gitlab merge request after rebase...since gitlab sadly can't do this on it's own.

You need:
- A Gitlab API token with read_api rights
- A merge request url
- Git access rights to the repo via password or key.

Run:

./mr_version_differ.py --token TOKEN --url URL

The script will instanciate an empty repository the first time it's run. The requested remote respository to which the MR belongs will be added as a remote. The script will let you choose two MR version. These will be fetched and range diffed, presenting the diff in stdout.


