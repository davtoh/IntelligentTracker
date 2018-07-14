# command to start documentation folder as "source"
$ sphinx-quickstart
# then rebane "source" to "documentation"

# command to generate initial files from root
$ sphinx-apidoc -F -H intelligent-tracker -A davtoh -V 0.1 -R 1 -o ./documentation ./intelligent_tracker ./intelligent_tracker/temp

# place this in conf.py on line 21
sys.path.insert(0, os.path.abspath("../")) # add RRtools path

# command to generate html
$ make html
# or
$ sphinx-build -b html . _build/html

# command to generate pdf
$ make latexpdf
