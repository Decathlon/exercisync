## Project life

This repository is not open sourced anymore, so this code stay here in archived mode and will not be maintained.
At DECATHLON we decided to build a new solution fastest, more scalable and richer in feature


## Credits
This project is based on https://github.com/cpfair/tapiriik code by Collin Fair.
Forked from https://github.com/Antash/exercisync by Anton Ashmarin

## Licensing
hub-decathlon is an Apache 2.0 Licensed open-source project.

## Translation
To use locale translation, it requires the package gettext.

To launch a new language, you have to generate the locale with : 
```
python3 manage.py makemessages -l 'fr'
```



Secondly, after translation (edition of po files), compile the files : 
```
python manage.py compilemessages
```

