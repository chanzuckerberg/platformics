.PHONY: codegen
codegen:
	python3 platformics/cli/main.py api generate --schemafile ./schema/test_app.yaml --output-prefix .

.PHONY: token
token:
	TOKEN=$$(python3 platformics/cli/main.py auth generate-token 111 --project 444:admin --expiration 99999);echo '{"Authorization":"Bearer '$$TOKEN'"}'

.PHONY: clean
clean:
	rm -rf api database database_migrations cerbos

.PHONY: restart
restart:
	supervisorctl restart test_app
