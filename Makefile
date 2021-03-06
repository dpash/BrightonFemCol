VIRTUAL_ENV?=".."
UWSGI_INI?="../uwsgi.yaml"
APP?=brightonfemcol


debug:
	$(VIRTUAL_ENV)/bin/python manage.py runserver 0.0.0.0:8000

install_requirements:
	$(VIRTUAL_ENV)/bin/pip install -r requirements.txt

pull:
	git pull

upgrade: pull install_requirements update_static update_db restart increment_cache

update_static:
	$(VIRTUAL_ENV)/bin/python manage.py collectstatic --noinput

update_db:
	$(VIRTUAL_ENV)/bin/python manage.py syncdb --noinput
	$(VIRTUAL_ENV)/bin/python manage.py migrate

create_admin:
	$(VIRTUAL_ENV)/bin/python manage.py create_admin

increment_cache:
	$(VIRTUAL_ENV)/bin/python manage.py increment_cache

init: init_db create_admin

init_db: update_db

watch:
	sass --watch $(APP)/static/scss:$(APP)/static/css

restart:
	touch uwsgi.ini

test_suave:
	$(VIRTUAL_ENV)/bin/python manage.py test suave --settings=$(APP).settings.test